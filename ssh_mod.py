import paramiko


class SSH_Connect(object):
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.con = paramiko.SSHClient()
        self.con.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.con.connect(host, username = self.username, password = self.password)
        self.c = self.con.invoke_shell()

    def send_command(self,line):
        self.c.send(line)
        return self.c.recv(9999)

    def close(self):
        self.c.close()
