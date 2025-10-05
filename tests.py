from bin.steam import authorize_and_get_cookies, sell_skin, get_inventory


def test_sell_skin():
    cookies = authorize_and_get_cookies(only_cookies=True)
    print(cookies)
    sell_skin(197.65, 46046538368, cookies)
    
    
def test_inventoy():
    cookies = authorize_and_get_cookies(only_cookies=True)
    print(get_inventory(cookies))
    
    
if __name__ == "__main__":
    test_inventoy()