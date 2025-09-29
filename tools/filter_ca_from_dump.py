import os, shutil
from asn1crypto import x509, pem

src = r"C:\Users\sidney.guerrero\Desktop\trust_certs\_dump"
dst = r"C:\Users\sidney.guerrero\Desktop\trust_certs"
os.makedirs(dst, exist_ok=True)

def load_all(path):
    for f in os.listdir(path):
        p=os.path.join(path,f)
        if not os.path.isfile(p): continue
        data=open(p,'rb').read()
        if pem.detect(data):
            for _t,_h,der in pem.unarmor(data, multiple=True):
                yield f, x509.Certificate.load(der)
        else:
            yield f, x509.Certificate.load(data)

for name, cert in load_all(src):
    subj = cert.subject.native; iss = cert.issuer.native
    is_ca = cert.basic_constraints_value.native.get('ca', False) if cert.basic_constraints_value else False
    self_signed = (subj == iss)
    print(f"{name} | CN={subj.get('common_name')} | IssuerCN={iss.get('common_name')} | CA={is_ca} | self-signed={self_signed}")
    if is_ca:
        shutil.copy2(os.path.join(src, name), os.path.join(dst, name))
print("Copiados CAs a:", dst)
