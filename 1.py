import requests

cookies = {
    '_lxsdk_cuid': '19429d09b55c8-00f512a229b048-26011851-1fa400-19429d09b55c8',
    '_lxsdk': '19429d09b55c8-00f512a229b048-26011851-1fa400-19429d09b55c8',
    'e_b_id_352126': '735819ae181ef9d09b7aead7948da5b7',
    'WEBDFPID': '7y4wy5zyu2uz509vzwz3vwy4285z333980570w90x649795826618w73-1746064009133-1735868324376GWESQEIfd79fef3d01d5e9aadc18ccd4d0c95071764',
    'BSID': 'Z2s2dU54bpl4GoxJJuqkjuaJF19UgrBotVnI3zsb73fhZOwD0lFtawjpu1woHOHwCDb7BEJt4aYEzTC1IjXg4w',
    'mall-epassport-token': 'Z2s2dU54bpl4GoxJJuqkjuaJF19UgrBotVnI3zsb73fhZOwD0lFtawjpu1woHOHwCDb7BEJt4aYEzTC1IjXg4w',
    'unionid': '19429d09b55c8-00f512a229b048-26011851-1fa400-19429d09b55c8',
    'mall-login-type': 'epassport',
    'msid': 'mtyxsj13067988046',
    'muid': '131447',
    'com.sankuai.groceryclient.vss.delivery_strategy': '',
    '_lxsdk_s': '19684600adb-83f-ca-bfb%7C%7C59',
    'logan_session_token': 'v49jfs7ftnbt7ejknwuu',
}

headers = {
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Origin': 'https://vss-grocery.meituan.com',
    'Pragma': 'no-cache',
    'Referer': 'https://vss-grocery.meituan.com/finance-alias/billDownload.html',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    'accept': 'application/json',
    'content-type': 'application/json',
    'm-appkey': 'fe_com.sankuai.fine.merchant',
    'm-traceid': '8961794644552177424',
    'mtgsig': '{"a1":"1.2","a2":1745978314472,"a3":"7y4wy5zyu2uz509vzwz3vwy4285z333980570w90x649795826618w73","a5":"ZhsBWJjkHRQTG1oHUTA7GqZZIW9WlI9SFX7oNZp+nGKelkkKZ9PMvg80WCXN3cHGAI==","a6":"h1.8QhTUEfDZ0vXcCwk6cBBdsjFZ3kmEWm4KW7k9rweGOxMYU0tsY3WApJEe663FQSlXjBOpBYORsYWbwBGNJpRM3wt8lVipSnQLnYjmfyPFfHQVQ777z86bYQJjHKm8EqUYF8OkQj1OYPb0VNzURA1fGDHx1Ve862kJcRfYenx1sP8fBDoNeuir6BeCD/3ccjvOTCi5tJ2Z72/+Rz3FGEj5TvJIau956cONjC4I7GKuJUXTRqPEVnWMP4RPLWFtv1djjw1uAUjuW7KjUqPXmJd8B00exEBwc/R29M9ie+3lzDbVt8MQYDAk9UySJLuoIoIOZ1vktjDHipTk5TO5tH1vdrWGy6X6v2ecL6yhtSRdvOLGB8gq8ILtHu1vVV1gc6ZnRXG6vQ4EpLkCSNuiNeWNIvf4hyeFVlDLhYQksG7ZpOaGsjkjeK9GEFHuBeEJbDhj6Si3gMt/dPfk4QPOnaZRBqxfeoc55/uJ4dWfdm55210=","a8":"edc3cd469d5f8817ac46d3458511a504","a9":"3.1.0,7,171","a10":"ab","x0":4,"d1":"e11b0fadb20aea7bac1bdb1f5311e5d4"}',
    'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    # 'Cookie': '_lxsdk_cuid=19429d09b55c8-00f512a229b048-26011851-1fa400-19429d09b55c8; _lxsdk=19429d09b55c8-00f512a229b048-26011851-1fa400-19429d09b55c8; e_b_id_352126=735819ae181ef9d09b7aead7948da5b7; WEBDFPID=7y4wy5zyu2uz509vzwz3vwy4285z333980570w90x649795826618w73-1746064009133-1735868324376GWESQEIfd79fef3d01d5e9aadc18ccd4d0c95071764; BSID=Z2s2dU54bpl4GoxJJuqkjuaJF19UgrBotVnI3zsb73fhZOwD0lFtawjpu1woHOHwCDb7BEJt4aYEzTC1IjXg4w; mall-epassport-token=Z2s2dU54bpl4GoxJJuqkjuaJF19UgrBotVnI3zsb73fhZOwD0lFtawjpu1woHOHwCDb7BEJt4aYEzTC1IjXg4w; unionid=19429d09b55c8-00f512a229b048-26011851-1fa400-19429d09b55c8; mall-login-type=epassport; msid=mtyxsj13067988046; muid=131447; com.sankuai.groceryclient.vss.delivery_strategy=; _lxsdk_s=19684600adb-83f-ca-bfb%7C%7C59; logan_session_token=v49jfs7ftnbt7ejknwuu',
}

params = {
    'yodaReady': 'h5',
    'csecplatform': '4',
    'csecversion': '3.1.0',
}

json_data = {
    'id': 3657522,
}

response = requests.post(
    'https://vss-grocery.meituan.com/api/vss/shepherd/platformSupplier/exportDetailFile',
    params=params,
    cookies=cookies,
    headers=headers,
    json=json_data,
)

print(response.text)