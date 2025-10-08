# Django-Aiogram3-Bot-Template

The telegram bot which written in aiogram framework integrated with django. Database built with postgresql

Just example of `echobot`

## Setup project

- Install all requirements using the command below
```shell
pip install -r requirements.txt
```
- Then copy the .env.example file to .env and customize yourself.
```shell
cp .env.example .env
```
- Add tables to your database.
```shell
python manage.py migrate
```

- Run the bot using the command below
```shell
python manage.py runbot
```

# 
- Create superuser for backend the command below
```shell
python manage.py createsuperuser
```

- Run the django project using the command below
```shell
python manage.py runserver
```

