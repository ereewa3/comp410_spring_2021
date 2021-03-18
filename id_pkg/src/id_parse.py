from id_pkg import LogParse
import pandas as pd
import re


class IdParse(LogParse):
    df = pd.DataFrame()

    def __init__(self, syslog_file):
        self.syslog_to_dataframe(syslog_file)

    def has_ip_spoofing(self):
        # https://pandas.pydata.org/docs/reference/api/pandas.Series.any.html
        return (self.df['ID'] == 106016).any()

    def has_acldrop(self):
        return (self.df['ID'] == 733100).any()

    def handle_asa_message(self, rec):
        """Implement ASA specific messages"""
    # %ASA-2-106016: Deny IP spoof from (IP_address) to IP_address on interface interface_name
        if rec['ID'] == 106016:
            m = re.search(r'from \((\d+\.\d+\.\d+\.\d+)\) to (\d+\.\d+\.\d+\.\d+) on interface (\w+)', rec['Text'])
            if m:
                rec['Source'] = m.group(1)
                rec['Destination'] = m.group(2)
                rec['Interface'] = m.group(3)
        # %ASA-4-733100: Object drop rate rate_ID exceeded.
        # Current burst rate is rate_val per second,
        # max configured rate is rate_val;
        # Current average rate is rate_val per second,
        # max configured rate is rate_val;
        # Cumulative total count is total_cnt

        if rec['ID'] == 733100:
            m = re.search( r'rate-(\d+) exceeded. Current burst rate is (\d+) per second, max configured rate is ('
                           r'\d+); Current average rate is (\d+) per second, max configured rate is (\d+); Cumulative '
                           r'total count is (\d+)', rec['Text'])
        if m:
            rec['DropRate'] = m.group(1)
            rec['BurstRate'] = m.group(2)
            rec['MaxConfigRate1'] = m.group(3)
            rec['CurrentAverageRate'] = m.group(4)
            rec['MaxConfigRate2'] = m.group(5)
            rec['TotalCount'] = m.group(6)
        return rec

    def handle_syslog_message(self, line):
        """Parses basic information out of a syslog file"""
        m = re.search(r'^(\w+ \w+ \w+ \d+:\d+:\d+) (\w+) : %(\w+)-(\d)-(\d+): (.+)', line)
        # If the re matched
        if m:
            return self.handle_asa_message({'Date': m.group(1),
                                            'Host': m.group(2),
                                            'Type': m.group(3),
                                            'Severity': int(m.group(4)),
                                            'ID': int(m.group(5)),
                                            'Text': m.group(6)})
        else:
            return {}

    def syslog_to_dataframe(self, syslog_file):
        """Returns a dataframe from a sample syslog file"""
        # Read the syslog file and parse it into our dataframe
        with open(syslog_file, encoding='utf-8') as f:
            for line in f:
                # Create a record to hold this line in the syslog file
                self.df = self.df.append(self.handle_syslog_message(line), ignore_index=True)
