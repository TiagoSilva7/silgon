import json, sys, urllib.request, urllib.error

url = 'http://127.0.0.1:5000/api/patients'
data = {
    'cpf':'31071655817',
    'name':'Teste',
    'tel_home':'',
    'tel_cell':'',
    'tel_msg':'',
    'contact_name':'',
    'email':'',
    'cep':'',
    'address':'',
    'number':'',
    'complement':'',
    'prof':'',
    'age':'',
    'weight':'',
    'height':''
}
req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req) as resp:
        print('STATUS', resp.status)
        print(resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('HTTPERROR', e.code)
    try:
        print(e.read().decode('utf-8'))
    except Exception as ex:
        print('Unable to read HTTPError body:', ex)
except Exception as e:
    print('ERR', e)
    sys.exit(1)
