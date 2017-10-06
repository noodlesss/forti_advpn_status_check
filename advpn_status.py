#from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.hlapi import *
import ssh_mod, time, smtplib, getpass, multiprocessing, logging, os

formatter = ('%(asctime)s : %(levelname)s : %(message)s')
logging.basicConfig(filename='logfile.log',format = formatter, level=logging.WARNING)

with open('host_list') as fl:
    host_list = fl.readlines()

def check_snmp(host, community):
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
               CommunityData(community, mpModel=0),
               UdpTransportTarget((host, 161)),
               ContextData(),
               ObjectType(ObjectIdentity('1.3.6.1.4.1.12356.101.12.2.2.1.20.1')))
    )

    if errorIndication:
        logging.warning('%s - %s' % (host,errorIndication))
    elif errorStatus:
        logging.warning('%s - %s at %s' % (host, errorStatus.prettyPrint(),
                            errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
        for name, val in varBinds:
            return val

def check_snmp2(host, community):
    cmdGen = cmdgen.CommandGenerator()

    errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
        cmdgen.CommunityData(community),
        cmdgen.UdpTransportTarget((host, 161)),
        '1.3.6.1.4.1.12356.101.12.2.2.1.20.1'
    )

    if errorIndication:
        logging.warning('%s - %s' %(host,errorIndication))
        return errorIndication
    elif errorStatus:
        logging.warning('%s - %s at %s' % (
                host,
                errorStatus.prettyPrint(),
                errorIndex and varBinds[int(errorIndex)-1] or '?'
        )
            )
        return 'snmp error, plz check logs.'
    else:
        for name, val in varBinds:
            return val
                #print('%s = %s' % (name.prettyPrint(), val.prettyPrint()))

def vpn_reset(host, username, password):
    command = 'diagnose vpn tunnel reset ADVPN-1'
    ssh_connect = ssh_mod.SSH_Connect(host,username,password)
    stdout = ssh_connect.send_command(command)
    ssh_connect.close()
    
def send_email(host, body):
    msg = ('From: vasya@example.com\r\nTo: petya@example.com\r\nSubject: %s ADVPN-1 change\r\n\r\n' %host)
    msg = msg + body
    s = smtplib.SMTP('mailserver ip', 587)
    s.sendmail('vasya@example.com', 'petya@example.com', msg)



def worker(host, username, password, community):
    while True:
        try:
            vpn_status = check_snmp(host, community) # checking VPN status
            if vpn_status == 1: # VPN status is down
                try:
                    vpn_reset(host, username, password) # reseting VPN
                    time.sleep(15)
                    vpn_status = check_snmp(host, community) # checking if VPN is up after reset
                    if vpn_status == 2:
                        status = 'up'
                        body = 'VPN status after reset is %s' %status
                    elif vpn_status == 1:
                        response = os.system("ping -c 1 %s >/dev/null 2>&1"  %host.replace('-fw', '-vr'))
                        if response != 0:
                            logging.warning('%s is down. Cannot reach %s' %(host, host.replace('-fw', '-vr')))
                            continue
                        status = 'down'
                        body = 'VPN status after reset is %s' %status
                        logging.warning('%s ADVPN is down' %host)
                    else:
                        status = vpn_status
                        body = 'SNMP error: %s' %status
                        logging.warning('%s SNMP error: %s' %(host, status))
                    send_email(host, body)
                except Exception as e:
                    logging.warning('cannot reset vpn of host: %s' %host)
                    body = "Couldn't reset ADVPN on %s. Error: %s" %(host,e)
                    send_email(host, body)
        except Exception as e:
            logging.warning('cannot check snmp status of host: %s. Error: %s' %(host,e))
            body = "Couldn't check SNMP status of ADVPN-1 on %s" %host
            send_email(host, body)
        time.sleep(60)


if __name__ == '__main__':
    username = input('username: ')
    password = getpass.getpass('password: ')
    community = input('community: ')
    jobs = []
    for host in host_list:
        p = multiprocessing.Process(target=worker, args=(host.rstrip(), username, password, community))
        jobs.append(p)
        p.start()
