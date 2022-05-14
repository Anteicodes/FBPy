from concurrent.futures import ThreadPoolExecutor
from FBPy.FBPy import Facebook, FacebookAPI
from itertools import count as ct
import zlib
from os import urandom
fb = FacebookAPI()
fb.login('','')
fb.dumps(open('kue.txt', 'w'))
print('dump')
x = 0
print(fb.get_name)
print(fb.GraphQL.test().json())
# print(fb.GraphQL.reactions('100050866593572_510920537280162', 'PRIDE').json())
