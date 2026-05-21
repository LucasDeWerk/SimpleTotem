content = open('/etc/hosts').read()

# Garante que 192.168.10.50 tem tanto 'sitef-server' quanto 'DELPHI'
if 'DELPHI' not in content:
    content = content.replace(
        '192.168.10.30 sitef-server',
        '192.168.10.30 sitef-server DELPHI'
    )
    open('/etc/hosts', 'w').write(content)

print(open('/etc/hosts').read())
