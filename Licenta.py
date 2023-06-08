from netmiko import ConnectHandler
import time


class CurrentIP(Exception):
    """ """
    pass


class NotARouter(Exception):
    """Nu router"""
    pass


class InsufficientBits(Exception):
    """ Octeti nu"""
    pass


class OctetsNotInRange(Exception):
    """Prea mari sau prea mici"""
    pass


class OctetsNotNumeric(Exception):
    """Nu avem octeti care sa contina doar cifre"""
    pass


class Echipament(object):
    def __init__(self, device_type, host, username, password):
        self.device_type = device_type
        self.host = host
        self.username = username
        self.password = password

    @staticmethod
    def connect_to_device(sesiune):
        return ConnectHandler(**sesiune)

    def __eq__(self, other):
        return self.host == other.host

    def __str__(self):
        return "Type: " + self.device_type + "\n" + "Hostname: " + self.hostname + "\n" + "Username: " + self.username + "\n"

    def get_hostname(self):
        sesiune = Echipament.connect_to_device(self.__dict__)
        output = sesiune.find_prompt().rstrip("#")
        sesiune.disconnect()
        return output

    def extract_config(self):
        sesiune = Echipament.connect_to_device(self.__dict__)
        sesiune.send_command("terminal length 0")
        output = sesiune.send_command("show run")
        hostname = sesiune.find_prompt()
        sesiune.disconnect()
        hostname = hostname.rstrip("#")
        try:
            with open(f"{hostname}.txt", "a") as f:
                f.write(output)
        except FileNotFoundError:
            print("File not found")

    def extract_config1(self):
        sesiune = Echipament.connect_to_device(self.__dict__)
        try:
            if not self.get_hostname().startswith("R"):
                raise NotARouter
        except NotARouter:
            print("Not a Router, no routing table")
        else:
            sesiune.send_command("terminal length 0")
            output = sesiune.send_command("show ip route")
            hostname = sesiune.find_prompt() + "+Routes"
            sesiune.disconnect()
            hostname = hostname.rstrip("#")
            try:
                with open(f"{hostname}.txt", "w") as f:
                    f.write(output)
            except FileExistsError:
                print("File has already been created")

    def apply_config(self, fisier):
        sesiune = Echipament.connect_to_device(self.__dict__)
        sesiune.send_config_from_file(fisier)
        sesiune.disconnect()

    @staticmethod
    def extrage_ip_direct(fisier):
        with open(fisier) as f:
            config1 = f.read().splitlines()
        list = [config1[k] for k in range(len(config1)) if config1[k].startswith("C")]
        list1 = [linie.split(" ")[8].split("/") for linie in list]
        list2 = []
        for list in list1:
            for li in list:
                if Echipament.ip_valid(li):
                    list2.append(li)
        return list2

    def extract_interfaces(self):
        pass

    @staticmethod
    def get_list_ips(fisier):
        list = []
        try:
            with open(fisier, "r") as f:
                li = f.read().splitlines()
        except FileNotFoundError:
            print("File doesn't exist")
        for ip in li:
            if Echipament.ip_valid(ip):
                list.append(ip)
        return list

    @staticmethod
    def dynamic_router(fisier):
        list_ip_routere = Echipament.get_list_ips(fisier)
        list_routere = [Echipament("cisco_ios", ip, "admin", "savnet") for ip in list_ip_routere]
        for router in list_routere:
            sesiune = Echipament.connect_to_device(router.__dict__)
            router.extract_config1()
            l = Echipament.extrage_ip_direct(sesiune.find_prompt() + "+Routes.txt")
            sesiune.send_config_set(["router rip", "version 2", "no auto-summary"])
            for ip_retea in l:
                sesiune.send_config_set(["router rip", f"network {ip_retea}"])
                print(ip_retea)
            sesiune.disconnect()

    def extragere_intefete(self, file_s):  # extrag interfetele din show run

        try:
            with open(file_s) as f2:
                config = f2.read().splitlines()
        except FileNotFoundError:
            print("Eroare la deschidere din cauza ca nu ii")
        j = 0
        with open(f"{self.get_hostname()}_interfaces.csv", "a") as g:  # hostname + interfaces in loc de interfaces.csv
            g.write("Interface, Enabled, IP, Netmask")
            g.write("\n")
        while j in range(len(config)):
            if config[j].startswith("interface"):
                with open(f"{self.get_hostname()}_interfaces.csv", "a") as g:
                    g.write(config[j].split(" ")[1])
                    g.write(",")
                j += 1

                if config[j].startswith("!"):
                    with open(f"{self.get_hostname()}_interfaces.csv", "a") as g:
                        g.write(" false, false")
                if config[j].startswith(" no") or (config[j + 1].strip(" ")).startswith("shutdown"):
                    with open(f"{self.get_hostname()}_interfaces.csv", "a") as g:
                        g.write(" false, false")
                        g.write("")
                    print("ok")
                elif config[j].startswith(" ip") and not config[j + 1].startswith(" shutdown"):
                    with open(f"{self.get_hostname()}_interfaces.csv", "a") as g:
                        g.write(f" true, {config[j].split(' ')[3]}, {config[j].split(' ')[4]}")
                        #
                        #
                        # g.write(",")
                    print("ok")
                elif config[j].startswith(" no") or (config[j + 1].strip(" ")).startswith("shutdown"):
                    with open(f"{self.get_hostname()}_interfaces.csv", "a") as g:
                        g.write(" true, false")
                with open(f"{self.get_hostname()}_interfaces.csv", "a") as g:
                    g.write("\n")
            j += 1

    # def check_connectivity(self):
    #     for ip in lista_ip:
    #         sesiune.send_command(f"ping {ip}")

    @staticmethod
    def ip_valid(adresa_ip):
        ip_form = adresa_ip.split(".")
        try:
            if len(ip_form) != 4:
                raise InsufficientBits
        except InsufficientBits:
            print("nu e ok ca nr de octeti")
        else:
            try:
                for octet in ip_form:
                    if not octet.isnumeric():
                        raise OctetsNotNumeric
            except OctetsNotNumeric:
                print("nu avem doar cifre")
            else:
                try:
                    for octet in ip_form:
                        if int(octet) not in range(0, 256):
                            raise OctetsNotInRange
                except OctetsNotInRange:
                    print("Nu sunt in interval")
                else:
                    return 1

# lista_ip = Echipament.get_list_ips("fisier.txt")
# print(lista_ip)
# lista_device = [Echipament("cisco_ios", ip, "admin", "savnet") for ip in lista_ip]
# for device in lista_device:
#    print(device.get_hostname())

# for device in lista_device:
#    device.apply_config("config.txt")

# lista_device[1].extract_config1()
# print(Echipament.extrage_ip_direct("R1#+Routes.txt"))
# lista_device[2].extract_config1()
# print("\n")
# print(Echipament.extrage_ip_direct("R2#+Routes.txt"))
# for linie in Echipament.extrage_linie("R1#+Routes.txt"):
#    print(linie.split(" ")[8].strip("/"))
# print(Echipament.extrage_ip_direct("R1#+Routes.txt"))
# Echipament.dynamic_router("fisier_ip.txt")
