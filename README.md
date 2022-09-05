# Attendshen Telegram Bot V2

# Project Overview
This project is called Attendshen, the Telegram bot that helps to facilitate attendance marking during class, events or seminars, so you don't have to! As a teaching assistant, I always find it time-consuming to look out for students in class and marking their attendance manually. As university students mostly use Telegram these days as their platform for communication, I decided to create a bot that they can use to easily mark their attendance by simply scanning a QR code.
# How does it work?
The main target of my application are mostly students in University, due to their frequent use of Telegram. However, this application can also be used by event administrators who are facilitating event attendance. Administrators must first get admin permissions on the Telegram Bot to begin. They will then have to create an event on the bot, which will generate a unique QR code that allows users of that event to scan and mark their own attendance. The admin can then view the current attendance of the users in the event to see who has or has not scanned their attendance, and allowing to mark down who was late or absent for administrative purposes.

From the user perspective, they would have to first enroll into a section, which denotes the event or class that they are in. Once they have enrolled into their section, they can start scanning QR codes that their event admin has displayed, in order to mark their attendance.
# Tools used
Python Flask - Backend to setup the Telegram Bot server
Telegram - The frontend of our Bot
MySQL - Database
Flask-SQLAlchemy - An object relational mapper in Pyton to allow connectivity to my MySQL database.

We mainly used 4 tools to build our bot, namely Python, MySQL as our database, TelegramBot API and SQLAlchemy. Instead of raw SQL in the Python script, we decided to use Flask-SQLAlchemy, which is a Python SQL toolkit and Object Relational Mapper (ORM). This translates python code to SQL, hence using this we can easily store objects into a relational database.
# References
https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/step_example.py
https://pypi.org/project/PyQRCode/
# Telegram Handle
[@attendshen_bot](https://t.me/attendshen_bot)
