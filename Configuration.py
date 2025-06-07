import os
from csv import DictReader

# local import
from const import TEST_REPO


class Configuration:
    def __init__(self, config_id):
        # config_id: aid_from-aid_to-scenario_id, e.g., a41a-a42a-b41
        target_app_id = config_id.split('-')[1]
        no_reset_apps = ['a41', 'a42', 'a43', 'a44', 'a45', 'a46', 'a47', 'a48', 'a49', 'a40', 'a16', 'a26', 'a28']
        if any([app_id in target_app_id for app_id in no_reset_apps]):
            self.no_reset = True
        else:
            self.no_reset = False
        parts = config_id.split('-')
        new_config_id = ''

        # Iterate through each part and apply the transformation
        for part in parts:
            # Replace everything after the first character with '*'
            new_part = part[0:2] + '*'  # Keep first two characters and add '*'
            # Add the transformed part to the new_config_id
            new_config_id += new_part + '-'

        # Remove the trailing '-' from the new_config_id
        new_config_id = new_config_id.rstrip('-')
        
        self.id = config_id

        # for c in configs:
        #     if c['id'] == new_config_id:
        #         self.id = config_id
        #         print(f"config_id: {config_id}")
        #         print(f"c['id']: {c['id']}")
        # assert self.id, 'Invalid config_id'
        self.pkg_from, self.act_from, self.pkg_to, self.act_to = Configuration.get_pkg_info(config_id)

    @staticmethod
    def get_pkg_info(config_id):
        # e.g., a41a-a42a-b41
        folder = config_id[:2]  # e.g., a4
        fpath = os.path.join(TEST_REPO, folder, folder + '.config')
        assert os.path.exists(fpath), 'Invalid app config path'
        pkg_from, act_from, pkg_to, act_to = '', '', '', ''
        with open(fpath, newline='') as cf:
            reader = DictReader(cf)  # aid,package,activity
            for row in reader:
                if row['aid'] == config_id.split('-')[0]:
                    pkg_from, act_from = row['package'], row['activity']
                elif row['aid'] == config_id.split('-')[1]:
                    pkg_to, act_to = row['package'], row['activity']
        assert pkg_from and pkg_to, 'Invalid config_id'
        return pkg_from, act_from, pkg_to, act_to
