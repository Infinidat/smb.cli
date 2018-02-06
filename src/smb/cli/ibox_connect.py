import infinisdk
from smb.cli.config import config_get
from infi.credentials_store import CLICredentialsStore


class SMBCrdentialsStore(CLICredentialsStore):
    def _get_file_folder(self):
        return ".smb.credentials_store"

    def authenticate(self, key, credentials):
        from infinisdk.core.exceptions import APICommandFailed
        if credentials is None:
            return False
        config = config_get(silent=True)
        try:
            ibox = infinisdk.InfiniBox(config['IboxAddress'], auth=(credentials.get_username(), credentials.get_password()))
            ibox.login()
            return True
        except APICommandFailed:
            return False

    def ask_credentials_prompt(self, key):
        print 'Connecting to InfiniBox ' + str(key)


def initiate_store(store_name):
    crdentials_store = SMBCrdentialsStore("all_iboxes")
    return crdentials_store.get_credentials(store_name)


class InfiSdkObjects(object):
    def __init__(self):
        self.config = config_get(silent=True)
        self.ibox = self.ibox_login()

    def get_ibox(self):
        return self.ibox

    def get_local_config(self):
        return self.config

    def get_cluster(self):
        cluster = self.ibox.host_clusters.choose(name=self.config['Cluster'])
        return cluster

    def ibox_login(self):
        '''tries to connect using credintal store'''
        store = initiate_store(self.config['IboxAddress'])
        ibox = infinisdk.InfiniBox(str(self.config['IboxAddress']),
                                   auth=(store.get_username(), store.get_password()))
        response = ibox.login()
        if response.status_code == 200:
            return ibox
        else:
            log_n_exit(logger, "Couldn't connect to InfiniBox with current credentials")
