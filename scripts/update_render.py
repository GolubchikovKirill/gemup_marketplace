#!/usr/bin/env python3
"""
Простой скрипт для обновления render.yaml
"""

import yaml
import os


def update_render_yaml():
    """Обновляет render.yaml для работы с DATABASE_URL"""

    # Читаем существующий файл
    with open('render.yaml', 'r') as file:
        config = yaml.safe_load(file)

    # Находим backend service
    for service in config['services']:
        if service['name'] == 'gemup-marketplace-backend':
            # Обновляем env на python
            service['env'] = 'python'

            # Убираем Docker настройки
            if 'dockerfilePath' in service:
                del service['dockerfilePath']
            if 'dockerContext' in service:
                del service['dockerContext']
            if 'dockerCommand' in service:
                del service['dockerCommand']

            # Добавляем Python команды
            service['buildCommand'] = 'pip install -r requirements.txt'
            service['startCommand'] = 'python main.py'

            # Обновляем environment variables
            env_vars = service.get('envVars', [])

            # Убираем старые PostgreSQL переменные
            env_vars = [var for var in env_vars if var['key'] not in [
                'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER',
                'POSTGRES_PASSWORD', 'POSTGRES_DB'
            ]]

            # Добавляем DATABASE_URL
            env_vars.append({
                'key': 'DATABASE_URL',
                'fromDatabase': {
                    'name': 'gemup-marketplace-db',
                    'property': 'connectionString'
                }
            })

            service['envVars'] = env_vars
            print("✅ Backend service updated")
            break

    # Находим frontend service
    for service in config['services']:
        if service['name'] == 'gemup-marketplace-frontend':
            # Обновляем на Node.js
            service['env'] = 'node'

            # Убираем Docker настройки
            if 'dockerfilePath' in service:
                del service['dockerfilePath']
            if 'dockerContext' in service:
                del service['dockerContext']

            # Добавляем Node.js команды
            service['buildCommand'] = 'cd nextjs && npm ci && npm run build'
            service['startCommand'] = 'cd nextjs && npm start'

            print("✅ Frontend service updated")
            break

    # Сохраняем обновленный файл
    with open('render.yaml', 'w') as file:
        yaml.dump(config, file, default_flow_style=False, indent=2)

    print("🎉 render.yaml successfully updated!")


if __name__ == "__main__":
    if not os.path.exists('render.yaml'):
        print("❌ render.yaml file not found!")
        exit(1)

    update_render_yaml()
