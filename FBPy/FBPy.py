from __future__ import annotations
from typing import (
    Generator,
    Optional,
    Union
)
from requests import Session
from bs4 import BeautifulSoup
from .utils import txt2json
from io import (
    TextIOWrapper,
    StringIO
)
import re

class InvalidEmailORPass(Exception):
    pass

class UserNotLoggin(Exception):
    pass

class InvalidID(Exception):
    pass

class FacebookError(Exception):
    pass

class FacebookBase(Session):
    headers: dict[str, str]
    BASE_URL = 'https://mbasic.facebook.com'
    def __init__(self, cookiefile: Optional[str] = None) -> None:
        super().__init__()
        self.headers = {
            'accept-language': 'en-US,en;q=0.9',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Linux",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36"
        }
        self.cookiefile = cookiefile
        if cookiefile:
            self.load_cookie(cookiefile)

    def endpoint(self, endp: str):
        return self.BASE_URL.rstrip() + '/' + endp.lstrip()

    @property
    def get_name(self):
        status = self.get(self.endpoint('profile.php')).text
        t = BeautifulSoup(status, 'html.parser').title
        if t:
            return t.text
        
    def load_cookie(self, file: str):
        for cookie in txt2json(open(file,'r').read()):
            cookie: dict[str,str]
            self.cookies.set(**cookie)

    def dump(self):
        if self.cookiefile:
            self.dumps(open(self.cookiefile, 'w'))

    def dumps(self, buf: Union[TextIOWrapper, StringIO]):
        buf.write('#Generated using FBPy\n')
        for c in self.cookies:
            buf.write('\t'.join(map(str, [
                c.domain,
                ['FALSE', 'TRUE'][c.domain_initial_dot],
                c.path, ['FALSE', 'TRUE'][c.secure],
                c.expires if not c.expires == None else 0,
                c.name,
                c.value
            ]))+'\n')

    def login(self, email: str, password: str):
        st = self.get(self.endpoint('login'))
        html=st.text
        post = dict((*re.findall(r'name="([\w]+)" value="([\w]+)"', html), ('login', 'Log In'), ('email', email), ('pass', password)))
        resp = self.post(self.endpoint(re.findall(r'action="(/[\w&-_=]+)"',html)[0].replace('amp;','')), data=post).text
        bs = BeautifulSoup(resp, 'html.parser')
        title = (bs.title.text if bs.title else '').lower()
        if bs.find_all('div', attrs={'id': 'login_error'}) or ('error' in title or 'log in' in title or 'find your' in title):
            if 'error' in title:
                raise FacebookError()
            elif 'find your' in title:
                return self.login(re.findall(r'/([\w.]+)\?', self.get(self.endpoint(email)).url)[0], password)
            raise InvalidEmailORPass('check your email & password')

class Friend:
    def __init__(self, add: str, requests: FacebookBase = FacebookBase(), name: Optional[str] = None) -> None:
        self.id = re.findall(r'\?id=([0-9]+)', add)[0]
        self.name = name
        self.add_friend = add.replace('amp;','')
        self.request = requests
    
    def add(self):
        return self.request.get(self.request.endpoint(self.add_friend))

    def friends(self) -> Generator[Friend, None, None]:
        resp = self.request.get(self.request.endpoint('profile.php'), params={'id': self.id, 'v':'friends'}).text
        while True:
            bs = BeautifulSoup(resp, 'html.parser').find_all('div', attrs={'id':'m_more_friends'})
            yield from [self.__class__(iP, self.request, u) for u, iP in zip(
                        [i.text for i in BeautifulSoup(resp, 'html.parser').find_all('a', attrs={'class':'ce'})],
                        re.findall(r'\"(/[\w/]+add_fr[.\w_&%/\-=;?]+)\"',resp)
                        )]
            if bs:
                resp = self.request.get(self.request.endpoint(bs[0].a['href'])).text
            else:
                break

    def __repr__(self) -> str:
        return f'name: {self.name} ID: {self.id}'

class Facebook(FacebookBase):
    def __init__(self, cookiefile:Optional[str] = None):
        super().__init__(cookiefile)

    @property
    def profile(self):
        return self.get(self.endpoint('profile.php'))
    
    def search_people(self, name: str) -> Generator[Friend, None, None]:
        resp = self.get(self.endpoint('search/people/'), params={'q': name, 'source':'filter', 'isTrending':0}).text
        while True:
            try:
                bs = BeautifulSoup(resp, 'html.parser').find_all('div', attrs={'id':'see_more_pager'})
                yield from [Friend(iP, self, u) for u, iP in zip(
                    [i.text for i in BeautifulSoup(resp, 'html.parser').find_all('div', attrs={'class':'ce'})],
                    re.findall(r'\"(/[\w/]+add_fr[.\w_&%/\-=;?]+)\"',resp)
                    )]
                if bs:
                    resp = self.get(bs[0].a['href']).text
                else:
                    break
            except Exception:
                break

