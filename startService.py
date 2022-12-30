import os
import subprocess

if __name__ == "__main__":
    if os.environ('watchTarget') == 'masterofmalts':
        curDir = os.getcwd()
        subprocess.call('python3' + curDir + '/masterOfMalts/watchMasterOfMalts.py')
    elif os.environ('watchTarget') == 'nickollsandperks':
        curDir = os.getcwd()
        subprocess.call('python3' + curDir + '/nickollsandperks/watchNickollsAndPerks.py')