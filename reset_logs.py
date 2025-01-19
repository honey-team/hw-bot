import os.path

if os.path.exists('./logs'):
    for i in os.listdir('./logs'):
        os.remove(f'./logs/{i}')
    os.rmdir('./logs')
