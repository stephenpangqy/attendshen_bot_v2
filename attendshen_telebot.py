import telebot
from telebot import types
import time
import datetime
import pyqrcode
from flask import Flask, redirect, url_for, request, render_template
import requests
from flask_sqlalchemy import SQLAlchemy

# Copyright 2021 Stephen Pang Qing Yang

app = Flask(__name__)

# SQL settings
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root@localhost:3306/attendshen'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 299}

db = SQLAlchemy(app)

bot_token = "1768510607:AAHNQq3NdVgRsMA42rnOYJx4F4sKTwiZ3lI" # must remove before pushing to github

bot = telebot.TeleBot(token=bot_token)

# SQLAlchemy Classes

class Users(db.Model):
    __tablename__ = 'users'

    chat_id = db.Column(db.Integer, nullable=False, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

class User_Sections(db.Model):
    __tablename__ = 'user_sections'

    chat_id = db.Column(db.Integer, nullable=False, primary_key=True)
    section = db.Column(db.String(100), nullable=False, primary_key=True)
    role = db.Column(db.String(100), nullable=False)

class Events(db.Model):
    __tablename__ = 'events'

    event_id = db.Column(db.Integer, nullable=False, primary_key=True)
    event_name = db.Column(db.String(100), nullable=False)
    section = db.Column(db.String(100), nullable=False)
    code_word = db.Column(db.String(20), nullable=False)
    completed = db.Column(db.String(1), nullable=False)

class Attendance(db.Model):
    __tablename__ = 'attendance'

    event_id = db.Column(db.Integer, nullable=False, primary_key=True)
    chat_id = db.Column(db.Integer, nullable=False, primary_key=True)
    mark_time = db.Column(db.Date,nullable=False)

class Late_Attendance(db.Model):
    __tablename__ = 'late_attendance'

    event_id = db.Column(db.Integer, nullable=False, primary_key=True)
    chat_id = db.Column(db.Integer, nullable=False, primary_key=True)
    status = db.Column(db.String(100), nullable=False)
    reason = db.Column(db.String(100))

class Sections(db.Model):
    __tablename__ = 'sections'

    section_id = db.Column(db.String(100), nullable=False, primary_key=True)
    section_count = db.Column(db.Integer, nullable=False)
    
# Dictionary to store users executing bot commands
command_user_dict = {}
# Dictionary to store temp enrolment objects
temp_enroll_dict = {}
# Dictionary to store temp event creation objects
temp_create_event_dict = {}
# Dictionary to store temp event modification objects
temp_modify_event_dict = {}
# Dictionary to store temp student objects
temp_student_dict = {}
# Dictionary to store view attendance objects
view_attendance_dict = {}
# Dictionary to store temp mark late objects
temp_mark_late_dict = {}

# Class to store student information while enrolling
class Temp_Enroll:
    def __init__(self, chat_id, section, message_id):
        self.chat_id = chat_id
        self.section = section
        self.message_id = message_id
    
    def getChatId(self):
        return self.chat_id
    def getSection(self):
        return self.section
    def getMessageId(self):
        return self.message_id
    def add_temp_enroll(self):
        temp_enroll_dict[self.chat_id] = self
        add_current_command(self.chat_id,"enroll")
    def del_temp_enroll(self):
        del temp_enroll_dict[self.chat_id]
        end_current_command(self.chat_id)
        
# Class to store information when creating an event 
class Temp_CreateEvent:
    def __init__(self):
        self.section = None
        self.message_id = None
        self.event_name = None
    
    def setSection(self,section):
        self.section = section
    def setMessageId(self,message_id):
        self.message_id = message_id
    def setEventName(self,event_name):
        self.event_name = event_name
    def getSection(self):
        return self.section
    def getEventName(self):
        return self.event_name
    def add_temp_create_event(self,chat_id):
        temp_create_event_dict[chat_id] = self
        add_current_command(chat_id,"create")
    def del_temp_create_event(self,chat_id):
        del temp_create_event_dict[chat_id]
        end_current_command(chat_id)

# Class to store information when modifying an event
class Temp_EventModify:
    def __init__(self):
        self.section = None
        self.message_id = None
        self.event_name = None
    
    def setSection(self,section):
        self.section = section
    def setMessageId(self,message_id):
        self.message_id = message_id
    def setEventName(self,event_name):
        self.event_name = event_name
    def getSection(self):
        return self.section
    def getMessageId(self):
        return self.message_id
    def getEventName(self):
        return self.event_name
        
    def add_temp_modify_event(self,chat_id,command):
        # command is either 'complete' or 'delete'
        temp_modify_event_dict[chat_id] = self
        add_current_command(chat_id,command)
    def del_temp_modify_event(self,chat_id):
        del temp_modify_event_dict[chat_id]
        end_current_command(chat_id)

# Class to store information when using a student's info in a section (delete,late attendance)
class Temp_Student:
    def __init__(self):
        self.section = None
        self.chat_id = None
        self.event_name = None
        self.status = None
        self.reason = None
    
    def setSection(self,section):
        self.section = section
    def setChatId(self,chat_id):
        self.chat_id = chat_id
    def setEventName(self,event_name):
        self.event_name = event_name
    def setStatus(self,status):
        self.status = status
    def setReason(self,reason):
        self.reason = reason
    def getSection(self):
        return self.section
    def getChatId(self):
        return self.chat_id
    def getEventName(self):
        return self.event_name
    def getStatus(self):
        return self.status
    def getReason(self):
        return self.reason
    
    def add_temp_student(self,chat_id):
        temp_student_dict[chat_id] = self
        add_current_command(chat_id,"delete_student")
    def del_temp_student(self,chat_id):
        del temp_student_dict[chat_id]
        end_current_command(chat_id)

class View_Attendance:
    def __init__(self):
        self.section = None
        self.event_id = None
        self.unchecked_list = []
    
    def setSection(self,section):
        self.section = section
    def setEventId(self,event_id):
        self.event_id = event_id
    def setUncheckedList(self,unchecked_list):
        self.unchecked_list = unchecked_list
    def getSection(self):
        return self.section
    def getEventId(self):
        return self.event_id
    def getUncheckedList(self):
        return self.unchecked_list
    
    def add_view_attendance(self,chat_id):
        view_attendance_dict[chat_id] = self
        add_current_command(chat_id,"view_attendance")
    def del_view_attendance(self,chat_id):
        del view_attendance_dict[chat_id]
        end_current_command(chat_id)
        
class Temp_Mark_Late:
    def __init__(self):
        self.section = None
        self.event_id = None
        self.chat_id = None
        self.status = None
        self.reason = None
        self.orig_message_id = None
    
    def setSection(self,section):
        self.section = section
    def setEventId(self,event_id):
        self.event_id = event_id
    def setChatId(self,chat_id):
        self.chat_id = chat_id
    def setReason(self,reason):
        self.reason = reason
    def setOrigMessageId(self,mid):
        self.orig_message_id = mid
    def setStatus(self,status):
        self.status = status
    def getSection(self):
        return self.section
    def getStatus(self):
        return self.status
    def getEventId(self):
        return self.event_id
    def getChatId(self):
        return self.chat_id
    def getReason(self):
        return self.reason
    def getOrigMessageId(self):
        return self.orig_message_id
    
    def add_mark_late(self,chat_id):
        temp_mark_late_dict[chat_id] = self
        add_current_command(chat_id,'mark_late')
    def del_mark_late(self,chat_id):
        del temp_mark_late_dict[chat_id]
        end_current_command(chat_id)

def getTempEnroll(chat_id):
    return temp_enroll_dict[chat_id]

def getTempCreateEvent(chat_id):
    return temp_create_event_dict[chat_id]

def getTempModifyEvent(chat_id):
    return temp_modify_event_dict[chat_id]

def getTempStudent(chat_id):
    return temp_student_dict[chat_id]

def getViewAttendance(chat_id):
    return view_attendance_dict[chat_id]

def getTempMarkLate(chat_id):
    return temp_mark_late_dict[chat_id]

def idExists(chat_id):
    # FUNCTION TO CHECK IF USER"S CHAT ID IS IN DATABASE
    users = Users.query.filter_by(chat_id=chat_id)
    for user in users:
        return True
    return False

def nameExists(name):
    # FUNCTION IN NAME REGISTERING, TO CHECK IF USER HAS PICKED A NAME THAT ALREADY EXISTS
    users = Users.query.filter_by(name=name)
    for user in users:
        return True
    return False

def doing_current_command(chat_id):
    # FUNCTION to check if user is currently performing a command
    if chat_id in command_user_dict:
        bot.send_message(chat_id,"You are currently using the command /" + command_user_dict[chat_id] + ". Please finish that command before calling another!")
        return False
    return True

def add_current_command(chat_id,action):
    # FUNCTION to add the user's current command into the command_user_dict when they have initiated a command.
    if chat_id not in command_user_dict:
        command_user_dict[chat_id] = action
        return True
    return False

def end_current_command(chat_id):
    # FUNCTION to remove the user's current command from command_user_dict once they have stopped doing the command
    if chat_id in command_user_dict:
        del command_user_dict[chat_id]

def isAdmin(chat_id):
    # FUNCTION TO CHECK IF USER IS AN ADMIN IN AT LEAST ONE SECTION
    admin_check = User_Sections.query.filter_by(chat_id=chat_id,role="Admin").first()
    if admin_check:
        return True
    bot.send_message(chat_id, "Sorry, you must be an Admin of a section in order to use this service.")
    return False

def retrieveSections(chat_id):
    # FUNCTION TO RETRIEVE SECTIONS THAT USER HAS ADMIN TO
    admin_id = chat_id
    user_sections = User_Sections.query.filter_by(chat_id=admin_id,role='Admin')
    section_list = []
    for sect in user_sections:
        section_list.append(sect.section)
    return section_list

def getSectionsMarkup(id,section_list,row_limit):
    keyboard = []
    row = []
    for section in section_list:
        row.append(types.InlineKeyboardButton(section,callback_data='pickSection'+ str(id) + ':' + section))
        if len(row) >= row_limit:
            keyboard.append(row)
            row = []
    if len(row) > 0:
        keyboard.append(row)
        
    return types.InlineKeyboardMarkup(keyboard)

def convertTime(datetime):
    # FUNCTION to convert Datetime (YYYY-MM-DD HH:MM:SS) to proper string time (e.g. 18 JUL 8:15 PM)
    string = ""
    month_dict = {"01":"JAN","02":"FEB","03":"MAR","04":"APR","05":"MAY","06":"JUN","07":"JUL","08":"AUG","09":"SEP","10":"OCT","11":"NOV","12":"DEC"}
    date_time = datetime.split(" ")
    date_list = date_time[0].split("-")
    string = date_list[2] + " " + month_dict[date_list[1]] + " "
    
    time_list = date_time[1].split(":")
    if int(time_list[0]) == 0:
        string += "12:" + time_list[1] + " AM"
    elif int(time_list[0]) >= 12: 
        hour = int(time_list[0]) - 12
        if int(time_list[0]) == 12:
            hour = int(time_list[0])
        string += str(hour) + ":" + time_list[1] + " PM"
    
    else:
        if int(time_list[0]) > 9:
            string += time_list[0] + ":" + time_list[1] + " AM"
        else:
            string += time_list[0][1] + ":" + time_list[1] + " AM"
            
    return string

@bot.message_handler(commands=['start'])
def welcome(message):
    msg_arr = message.text.split(" ")
    ongoing_action = doing_current_command(message.chat.id)
    if not ongoing_action:
        return
    # DEFAULT WELCOME MESSAGE WHEN BOT IS STARTED
    if len(msg_arr) == 1:
        usedBefore = idExists(message.chat.id)
        # check if chat id exists
        if usedBefore:
            user = Users.query.filter_by(chat_id=message.chat.id).first()
            name = user.name
            bot.send_message(message.chat.id,"Welcome back, " + name + ". I am Hanabi, the attendance-taker bot. Just in case you forgot the commands you can use:\n\n/enroll (section number) \n\nUse this command to enroll into your section. To mark your attendance, simply scan the QR code shown to you by your prof or instructor, and click on 'start'.\n\n/updatename\n\nThis is to change your display name in our attendance-taking).\n\nIf you find any errors with me, please let the developer @StepUpUrGame know.")
        else:
            bot.send_message(message.chat.id,"Welcome! I am Hanabi, the bot that handles your all your attendance-taking needs.\n\nFor Students: \n\n /enroll (section number) \n\nUse this command to enroll into your section. To mark your attendance, simply scan the QR code shown to you by your prof or instructor, and click on 'start'.\n\nIf you find any errors with me, please let the developer @StepUpUrGame know.")

        if not usedBefore:
            msg = bot.send_message(message.chat.id,"It looks like this is your first time using me. Please enter your name in the next chat bubble; make sure your instructors can recognize your name.")
            bot.register_next_step_handler(msg, register)
            return
    # FOR STUDENTS WHO ARE CHECKING IN THEIR ATTENDANCE IN THEIR SECTION
    else:
        user_chat_id = message.chat.id
        password = msg_arr[1]
        # Search for event with that password
        event = Events.query.filter_by(code_word=password).first()
        # If no event with that code exists
        if not event:
            bot.send_message(user_chat_id, "This event does not exist. Please contact your instructor if you think it is a mistake.")
            return
        user_section = User_Sections.query.filter_by(chat_id=user_chat_id,section=event.section,role='Student').first()
        # If user is not enrolled into that section
        if not user_section:
            bot.send_message(user_chat_id, "This check-in is for section " + event.section + ". You are not enrolled in this section!")
            return
        # If event has ended or closed check-ins
        if event.completed == "1":
            bot.send_message(user_chat_id, "The instructor/admin has closed this event, you can no longer mark your attendance. Please contact your instructor / TAs if you are late.")
            return
        
        # If user already checked in to that event
        already_attended = Attendance.query.filter_by(chat_id=user_chat_id,event_id=event.event_id).first()
        if already_attended:
            bot.send_message(user_chat_id, "You have already marked your attendance for this event.")
            return
        
        # Creates attendance check in
        try:
            new_attendance = Attendance(event_id=event.event_id,chat_id=user_chat_id,mark_time=datetime.datetime.now())
            db.session.add(new_attendance)
            db.session.commit()
            bot.send_message(user_chat_id,"✅ You have successfully marked your attendance for section " + event.section + "'s " + event.event_name)
        except Exception as e:
            bot.reply_to(message,"An error occurred while processing your check-in " + str(e) + ". Please contact your instructor or notify the developer.")
        
def register(message):
    user_chat_id = message.chat.id
    name = message.text.strip()
    if name == "":
        msg = bot.reply_to(message,'Your name cannot be empty. Please enter your name again!')
        bot.register_next_step_handler(msg,register)
        return
    elif "/" in name:
        msg = bot.reply_to(message,"Your name shouldn't have a / in it (you have accidentally entered a command). Please enter your name again!")
        bot.register_next_step_handler(msg,register)
        return
    elif len(name) > 100:
        msg = bot.reply_to(message,"Your name cannot be longer than 100 characters. Please enter your name again!")
        bot.register_next_step_handler(msg,register)
        return

    else:
        # Check if similar name in that section.
        exist_check = nameExists(name)
        if exist_check:
            msg = bot.reply_to(message,"Sorry, but it looks like someone already has that name. Please enter a new name.")
            bot.register_next_step_handler(msg,register)
        else:
            new_user = Users(chat_id=user_chat_id,name=name)
            try:
                db.session.add(new_user)
                db.session.commit()
                bot.reply_to(message,"Thank you, " + name + ", you have successfully registered. You may now enroll into your sections using the /enroll command.")
            except Exception as e:
                bot.reply_to(message,"An error occurred while processing your registration: " + str(e) + ". Please contact your instructor or notify the developer.")

# For Students and Admins to change their name #####################
@bot.message_handler(commands=["updatename"])
def updateName(message):
    user_id = message.chat.id
    ongoing_action = doing_current_command(user_id)
    if not ongoing_action:
        return
    # Check if user already registered
    id_exists = idExists(user_id)
    if not id_exists:
        bot.reply_to(message,"You have not registered in our database, please type /start and register your name with us first before enrolling!")
        return
    
    msg = bot.reply_to(message,"Please enter your new name, make sure that it is not longer than 100 characters.")
    add_current_command(user_id,"updatename")
    bot.register_next_step_handler(msg,confirmName)
    
def confirmName(message):
    user_chat_id = message.chat.id
    name = message.text.strip()
    if name == "":
        msg = bot.reply_to(message,'Your name cannot be empty. Please enter your name again!')
        bot.register_next_step_handler(msg,confirmName)
        return
    elif "/" in name:
        msg = bot.reply_to(message,"Your name shouldn't have a / in it (you have accidentally entered a command). Please enter your name again!")
        bot.register_next_step_handler(msg,confirmName)
        return
    elif len(name) > 100:
        msg = bot.reply_to(message,"Your name cannot be longer than 100 characters. Please enter your name again!")
        bot.register_next_step_handler(msg,confirmName)
        return

    else:
        # Check if similar name in that section.
        exist_check = nameExists(name)
        if exist_check:
            msg = bot.reply_to(message,"Sorry, but it looks like someone already has that name. Please enter a new name.")
            bot.register_next_step_handler(msg,confirmName)
            return
        else:
            try:
                current_user = Users.query.filter_by(chat_id=user_chat_id).first()
                current_user.name = name
                db.session.commit()
                bot.reply_to(message,"Your name has been successfully changed to " + name +".")
            except Exception as e:
                bot.reply_to(message,"An error occurred while processing your name change: " + str(e) + ". Please contact your instructor or notify the developer.")
    
    end_current_command(user_chat_id)
    
# For Students to register into their section. ##############################################################################
@bot.message_handler(commands=['enroll']) # /enroll wad2-g2
def enroll(message):
    user_chat_id = message.chat.id
    # Check if user is performing an action already.
    ongoing_action = doing_current_command(user_chat_id)
    if not ongoing_action:
        return
    # Check if user already registered
    id_exists = idExists(user_chat_id)
    if not id_exists:
        bot.reply_to(message,"You have not registered in our database, please type /start and register your name with us first before enrolling!")
        return
    
    chosen_section = message.text[7:].strip().lower()
    section_obj_list = Sections.query.all()
    sections = []
    for sect in section_obj_list:
        sections.append(sect.section_id)
    if chosen_section == "":
        bot.reply_to(message, "Please enter your section after the /enroll command (e.g. /enroll esd-g5)")
    elif chosen_section not in sections:
        bot.reply_to(message, "Section not found! Please enter a valid section!")

    else:
        # Check if user is already enrolled in that section
        section_exist = User_Sections.query.filter_by(chat_id=user_chat_id,section=chosen_section).first()
        if section_exist:
            bot.reply_to(message, "You are already enrolled into this section, " + chosen_section)
            return
        keyboard = [[types.InlineKeyboardButton("Yes",callback_data='enroll:yes'),types.InlineKeyboardButton("No",callback_data='enroll:no')]]
        markup = types.InlineKeyboardMarkup(keyboard)
        temp_enroll = Temp_Enroll(user_chat_id,chosen_section,message.message_id)
        msg = bot.send_message(user_chat_id,"You are going to register for the following section:"  + "\n\nSection: "+ temp_enroll.getSection() +"\n\nConfirm?", reply_markup=markup)
        temp_enroll.add_temp_enroll()
        
@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "enroll")
def confirmEnroll(query):
    try:
        response = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        temp_enroll = getTempEnroll(user_id)
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        # Stop Enrolment if "No" is pressed
        if response == "no":
            bot.edit_message_text('Enrolment has been cancelled.',user_id,message_id)
        # Process Enrolment if "Yes" is pressed.
        else:
            new_add = User_Sections(chat_id=temp_enroll.getChatId(),section=temp_enroll.getSection(),role='Student')
            db.session.add(new_add)
            section = Sections.query.filter_by(section_id=temp_enroll.getSection()).first()
            section.section_count += 1
            db.session.commit()
            bot.edit_message_text("Your enrolment to " + temp_enroll.getSection() + " has been successful. You may now scan QR codes of this section to mark your attendance.",user_id,message_id)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        
    end_current_command(query.from_user.id)
    
# Admin command to create an event for their section ###################################################################
@bot.message_handler(commands=['create'])
def pickSection(message):
    ongoing_action = doing_current_command(message.chat.id)
    if not ongoing_action:
        return
    admin_check = isAdmin(message.chat.id)
    if not admin_check:
        return
    section_list = retrieveSections(message.chat.id)
    markup = getSectionsMarkup(1,section_list,3)
    new_temp_create = Temp_CreateEvent()
    new_temp_create.add_temp_create_event(message.chat.id)
    bot.send_message(message.chat.id,'Please pick the section that you want to create an event for.',reply_markup=markup)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "pickSection1")
def enterEventName(query):
    try:
        section = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        temp_create = getTempCreateEvent(user_id)
        temp_create.setSection(section)
        temp_create.setMessageId(message_id)
        
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        
        msg = bot.edit_message_text('You have chosen section '+ section +'.\n\nPlease enter a name for your event in the next chat bubble (e.g. Week 1 Attendance)',user_id,message_id)
        bot.register_next_step_handler(msg,confirmEvent)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_create.del_temp_create_event(user_id)

def confirmEvent(message):
    event_name = message.text
    chat_id = message.chat.id
    temp_create = getTempCreateEvent(chat_id)
    section = temp_create.getSection()
    # Check if event name already exists in that particular section
    got_event = Events.query.filter_by(section=section,event_name=event_name).first()
    if got_event:
        msg = bot.reply_to(message, "There is already an event with the exact name in your section. Please enter another event name!")
        bot.register_next_step_handler(msg,confirmEvent)
        return

    temp_create.setEventName(event_name)
    keyboard = [[types.InlineKeyboardButton("Yes",callback_data='create:yes'),types.InlineKeyboardButton("No",callback_data='create:no')]]
    markup = types.InlineKeyboardMarkup(keyboard)
    bot.reply_to(message,"Please confirm the following details of your event:\n\nEvent Name: " + temp_create.getEventName() + "\nSection: " + temp_create.getSection() + "\n\nConfirm?", reply_markup=markup)
    
@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "create")
def createEvent(query):
    temp_create = getTempCreateEvent(query.from_user.id)
    try:
        response = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        
        if response == "no":
            # Cancel event creation
            bot.edit_message_text('Event Creation has been cancelled',user_id,message_id)
            temp_create.del_temp_create_event(user_id)
        else:
            # Process event creation
            # CREATING A RANDOMLY GENERATED CODE WORD
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for i in range(20))
            # Check if got similar code
            got_event = Events.query.filter_by(code_word=password).first()
            while got_event:
                password = ''.join(secrets.choice(alphabet) for i in range(20))
                got_event = Events.query.filter_by(code_word=password).first()

            new_event = Events(event_name=temp_create.getEventName(),section=temp_create.getSection(),code_word=password,completed=0)
            db.session.add(new_event)
            db.session.commit()
            # Creating the QR code with link attached.
            url=pyqrcode.create("https://t.me/attendshen_bot?start="+password)
            url.png('qrcode.png',scale=15)
            bot.send_chat_action(user_id,'upload_document')
            bot.send_document(user_id,open('qrcode.png','rb'))
            bot.send_message(user_id,"The event, " + temp_create.getEventName() + " for section " + temp_create.getSection() + " has been created. Students may start checking in their attendance by scanning the QR code above. \n\n If scanning the QR code is not possible, you can also ask them to enter the following command: /start " + password)
            temp_create.del_temp_create_event(user_id)

    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_create.del_temp_create_event(user_id)

# Admin command to mark an event as complete. ####################################################################
@bot.message_handler(commands=["complete"]) 
def pickSection2(message):
    try:
        ongoing_action = doing_current_command(message.chat.id)
        if not ongoing_action:
            return
        admin_check = isAdmin(message.chat.id)
        if not admin_check:
            return
        section_list = retrieveSections(message.chat.id)
        markup = getSectionsMarkup(2,section_list,3)
        new_temp_modify = Temp_EventModify()
        new_temp_modify.add_temp_modify_event(message.chat.id,'complete')
        bot.send_message(message.chat.id,'Please pick the section that you want to mark an event as complete for.',reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        new_temp_modify.del_temp_modify_event(message.chat.id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "pickSection2")
def pickEvent(query):
    try:
        section = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        temp_modify = getTempModifyEvent(user_id)
        temp_modify.setSection(section)
        temp_modify.setMessageId(message_id)
        
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        # Generate existing incomplete events of the section
        incomplete_events = Events.query.filter_by(section=section,completed=0)

        row_limit = 4 # MODIFY IF REQUIRED
        keyboard = []
        row = []
        for event in incomplete_events:
            row.append(types.InlineKeyboardButton(event.event_name,callback_data='confirmComplete:'+ str(event.event_id)))
            if len(row) >= row_limit:
                keyboard.append(row)
                row = []
        if len(row) > 0:
            keyboard.append(row)
        
        # If there are no events
        if len(keyboard) == 0:
            bot.edit_message_text("You have no events. Use /create to create a new one for your section.",user_id,message_id)
            temp_modify.del_temp_modify_event(user_id)
            return
        bot.edit_message_text('You have chosen section '+ section +'.\n\nPick an event that you want to mark as complete. Students will no longer be able to check their attendance for this event.',user_id,message_id)
        markup = types.InlineKeyboardMarkup(keyboard)
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=markup)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_modify.del_temp_modify_event(user_id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "confirmComplete")
def confirmComplete(query):
    user_id = query.from_user.id
    message_id = query.message.id
    temp_modify = getTempModifyEvent(user_id)
    new_markup = types.InlineKeyboardMarkup([])
    bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
    try:
        event_id = query.data.split(":")[1]
        event_name = Events.query.filter_by(event_id=event_id).first().event_name
        temp_modify.setEventName(event_name)
        bot.edit_message_text('You have chosen section '+ temp_modify.getSection() +'.\n\nYou have chosen to mark the following event as complete: '+ temp_modify.getEventName() +' \n\nConfirm? Be reminded that your students will no longer be able to check their attendance for this event.',user_id,message_id)
        keyboard = [[types.InlineKeyboardButton("Yes",callback_data='completeEvent:yes'),types.InlineKeyboardButton("No",callback_data='completeEvent:no')]]
        markup = types.InlineKeyboardMarkup(keyboard)
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=markup)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_modify.del_temp_modify_event(user_id)
 
@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "completeEvent")
def completeEvent(query):
    user_id = query.from_user.id
    message_id = query.message.id
    temp_modify = getTempModifyEvent(user_id)
    new_markup = types.InlineKeyboardMarkup([])
    bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
    try:
        response = query.data.split(":")[1]
        if response == "no":
            # cancel event completion
            bot.edit_message_text('Event Completion has been cancelled.',user_id,message_id)
            temp_modify.del_temp_modify_event(user_id)   
        else:
            # Proceed with event completion
            event = Events.query.filter_by(section=temp_modify.getSection(),event_name=temp_modify.getEventName()).first()
            event.completed = 1
            db.session.commit()
            bot.edit_message_text('The event, ' + temp_modify.getEventName() + ' for section ' + temp_modify.getSection() + ' has been marked as complete. Students can no longer check in their attendance for that event.',user_id,message_id)
            temp_modify.del_temp_modify_event(user_id)
        
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_modify.del_temp_modify_event(user_id)      

# Admin command to remove an event from their section.#############################################################
@bot.message_handler(commands=["delete"])
def pickSection3(message):
    try:
        ongoing_action = doing_current_command(message.chat.id)
        if not ongoing_action:
            return
        admin_check = isAdmin(message.chat.id)
        if not admin_check:
            return
        section_list = retrieveSections(message.chat.id)
        markup = getSectionsMarkup(3,section_list,3)
        new_temp_modify = Temp_EventModify()
        new_temp_modify.add_temp_modify_event(message.chat.id,'delete')
        bot.send_message(message.chat.id,'Please pick the section that you want to delete an event for.',reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        new_temp_modify.del_temp_modify_event(message.chat.id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "pickSection3")
def pickEvent2(query):
    try:
        section = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        temp_modify = getTempModifyEvent(user_id)
        temp_modify.setSection(section)
        temp_modify.setMessageId(message_id)
        
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        # Generate existing incomplete events of the section
        events = Events.query.filter_by(section=section)
        row_limit = 4 # MODIFY IF REQUIRED
        keyboard = []
        row = []
        for event in events:
            row.append(types.InlineKeyboardButton(event.event_name,callback_data='confirmDelete:'+ str(event.event_id)))
            if len(row) >= row_limit:
                keyboard.append(row)
                row = []
        if len(row) > 0:
            keyboard.append(row)
        # If there are no events
        if len(keyboard) == 0:
            bot.edit_message_text("You have no events. Use /create to create a new one for your section.",user_id,message_id)
            temp_modify.del_temp_modify_event(user_id)
            return
        bot.edit_message_text('You have chosen section '+ section +'.\n\nPick an event that you want to delete. This will erase all student attendance records for that particular event.',user_id,message_id)
        markup = types.InlineKeyboardMarkup(keyboard)
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=markup)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_modify.del_temp_modify_event(user_id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "confirmDelete")
def confirmDelete(query):
    user_id = query.from_user.id
    message_id = query.message.id
    temp_modify = getTempModifyEvent(user_id)
    new_markup = types.InlineKeyboardMarkup([])
    bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
    try:
        event_id = query.data.split(":")[1]
        event_name = Events.query.filter_by(event_id=event_id).first().event_name
        temp_modify.setEventName(event_name)
        bot.edit_message_text('You have chosen section '+ temp_modify.getSection() +'.\n\nYou have chosen to delete the following event: '+ temp_modify.getEventName() +' \n\nConfirm? Be reminded that this will delete all attendance records for this event.',user_id,message_id)
        keyboard = [[types.InlineKeyboardButton("Yes",callback_data='deleteEvent:yes'),types.InlineKeyboardButton("No",callback_data='deleteEvent:no')]]
        markup = types.InlineKeyboardMarkup(keyboard)
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=markup)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_modify.del_temp_modify_event(user_id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "deleteEvent")
def deleteEvent(query):
    user_id = query.from_user.id
    message_id = query.message.id
    temp_modify = getTempModifyEvent(user_id)
    new_markup = types.InlineKeyboardMarkup([])
    bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
    try:
        response = query.data.split(":")[1]
        if response == "no":
            # cancel event deletion
            bot.edit_message_text('Event Deletion has been cancelled.',user_id,message_id)
            temp_modify.del_temp_modify_event(user_id)   
        else:
            # Proceed with event deletion
            event = Events.query.filter_by(section=temp_modify.getSection(),event_name=temp_modify.getEventName()).first()
            attendances = Attendance.query.filter_by(event_id=event.event_id)
            late_attendances = Late_Attendance.query.filter_by(event_id=event.event_id)
            to_delete_list = []
            for attendance in attendances:
                to_delete_list.append(attendance)
            for late_attendance in late_attendances:
                to_delete_list.append(late_attendance)
            for e in to_delete_list:
                db.session.delete(e)
            db.session.delete(event)
            db.session.commit()
            bot.edit_message_text('The event, ' + temp_modify.getEventName() + ' for section ' + temp_modify.getSection() + ' and all its attendance records have been deleted successfully.',user_id,message_id)
            temp_modify.del_temp_modify_event(user_id)
        
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_modify.del_temp_modify_event(user_id)  

# Admin command to delete a user from the section they have admin in. #####################################################################
@bot.message_handler(commands=['delete_student'])
def pickSection4(message):
    try:
        ongoing_action = doing_current_command(message.chat.id)
        if not ongoing_action:
            return
        admin_check = isAdmin(message.chat.id)
        if not admin_check:
            return
        section_list = retrieveSections(message.chat.id)
        markup = getSectionsMarkup(4,section_list,3)
        new_temp_student = Temp_Student()
        new_temp_student.add_temp_student(message.chat.id)
        bot.send_message(message.chat.id,'Please pick the section that you want to delete an event for.',reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        new_temp_student.del_temp_student(message.chat.id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "pickSection4")
def pickStudent(query):
    try:
        section = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        temp_student = getTempStudent(user_id)
        temp_student.setSection(section)
        
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        # Generate existing incomplete events of the section
        students = User_Sections.query.filter_by(section=section,role='Student')
        row_limit = 4 # MODIFY IF REQUIRED
        keyboard = []
        row = []
        for student in students:
            name = Users.query.filter_by(chat_id=student.chat_id).first().name
            row.append(types.InlineKeyboardButton(name,callback_data='pickStudent:'+ str(student.chat_id)))
            if len(row) >= row_limit:
                keyboard.append(row)
                row = []
        if len(row) > 0:
            keyboard.append(row)
        bot.edit_message_text('You have chosen section '+ section +'.\n\nPick a student that you want to remove from your section. This will erase all attendance records of the student from this section.',user_id,message_id)
        markup = types.InlineKeyboardMarkup(keyboard)
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=markup)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_student.del_temp_student(user_id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "pickStudent")
def confirmDeleteStu(query):
    user_id = query.from_user.id
    message_id = query.message.id
    temp_student = getTempStudent(user_id)
    new_markup = types.InlineKeyboardMarkup([])
    bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
    try:
        chat_id = query.data.split(":")[1]
        temp_student.setChatId(chat_id)
        name = Users.query.filter_by(chat_id=chat_id).first().name
        bot.edit_message_text('You have chosen section '+ temp_student.getSection() +'.\n\nYou have chosen to remove the following student: '+ name +' \n\nConfirm? Be reminded that this will delete all attendance records for that particular user in this section.',user_id,message_id)
        keyboard = [[types.InlineKeyboardButton("Yes",callback_data='deleteStudent:yes'),types.InlineKeyboardButton("No",callback_data='deleteStudent:no')]]
        markup = types.InlineKeyboardMarkup(keyboard)
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=markup)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_student.del_temp_student(user_id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "deleteStudent")
def deleteStu(query):
    try:
        response = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        temp_student = getTempStudent(user_id)
        
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        if response == "no":
            # Cancel student deletion
            bot.edit_message_text('Student Deletion has been cancelled.',user_id,message_id)
            temp_student.del_temp_student(user_id)   
        else:
            # Proceed with event deletion
            to_delete_list = []
            user_section = User_Sections.query.filter_by(chat_id=temp_student.getChatId(),section=temp_student.getSection()).first()
            section_events = Events.query.filter_by(section=temp_student.getSection())
            for event in section_events:
                event_id = event.event_id
                attendance = Attendance.query.filter_by(event_id=event_id,chat_id=temp_student.getChatId()).first()
                if attendance:
                    to_delete_list.append(attendance)
                else:
                    late_attendance = Late_Attendance.query.filter_by(event_id=event_id,chat_id=temp_student.getChatId()).first()
                    if late_attendance:
                        to_delete_list.append(late_attendance)

            for a in to_delete_list:
                db.session.delete(a)
            db.session.delete(user_section)
            db.session.commit()
            name = Users.query.filter_by(chat_id=temp_student.getChatId()).first().name
            bot.edit_message_text('The student, ' + name + ' has been removed from section ' + temp_student.getSection() + ' and all their attendance records have been deleted successfully.',user_id,message_id)
            temp_student.del_temp_student(user_id)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_student.del_temp_student(user_id)

# ADMIN COMMAND TO VIEW ATTENDANCE ###############################################################
@bot.message_handler(commands=["view_attendance"]) 
def pickSection5(message):
    try:
        ongoing_action = doing_current_command(message.chat.id)
        if not ongoing_action:
            return
        admin_check = isAdmin(message.chat.id)
        if not admin_check:
            return
        section_list = retrieveSections(message.chat.id)
        markup = getSectionsMarkup(5,section_list,3)
        new_view_attendance = View_Attendance()
        new_view_attendance.add_view_attendance(message.chat.id)
        bot.send_message(message.chat.id,'Please pick the section that you want to view attendance for.',reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        new_view_attendance.del_view_attendance(message.chat.id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "pickSection5")
def pickEvent2(query):
    try:
        section = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        new_view_attendance = getViewAttendance(user_id)
        new_view_attendance.setSection(section)
        
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        # Generate existing incomplete events of the section
        events = Events.query.filter_by(section=section)
        row_limit = 4 # MODIFY IF REQUIRED
        keyboard = []
        row = []
        for event in events:
            row.append(types.InlineKeyboardButton(event.event_name,callback_data='view_att:'+ str(event.event_id)))
            if len(row) >= row_limit:
                keyboard.append(row)
                row = []
        if len(row) > 0:
            keyboard.append(row)
        # If there are no events
        if len(keyboard) == 0:
            bot.edit_message_text("You have no events. Use /create to create a new one for your section.",user_id,message_id)
            new_view_attendance.del_view_attendance(user_id)
            return
        bot.edit_message_text('You have chosen section '+ section +'.\n\nPick an event that you want to check attendance for.',user_id,message_id)
        markup = types.InlineKeyboardMarkup(keyboard)
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=markup)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        new_view_attendance.del_view_attendance(user_id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "view_att")
def displayAttendance(query):
    try:
        event_id = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        new_view_attendance = getViewAttendance(user_id)
        new_view_attendance.setEventId(event_id)
        event_name = Events.query.filter_by(event_id=event_id).first().event_name
        students_in_section = User_Sections.query.filter_by(section=new_view_attendance.getSection(),role='Student')
        attendance = Attendance.query.filter_by(event_id=event_id)
        late_attendance = Late_Attendance.query.filter_by(event_id=event_id)
        
        display_message = "Here is the attendance for event, '" + event_name + "' of section, " + new_view_attendance.getSection() + ".\n\n✅ THOSE WHO CHECKED IN ✅\n\n"
        all_student_name_id_dict = {}
        on_time_student_id_dict = {}
        late_student_id_dict = {}
        for student in students_in_section:
            name = Users.query.filter_by(chat_id=student.chat_id).first().name
            all_student_name_id_dict[student.chat_id] = name
            
        # adding those who have checked in on time
        for att in attendance:
            time_string = convertTime(str(att.mark_time))
            on_time_student_id_dict[att.chat_id] = time_string
        # adding those who have checked in late
        for late_att in late_attendance:
            late_student_id_dict[late_att.chat_id] = (late_att.status,late_att.reason)
        
        # Displaying those who have checked in on time
        for student_id in on_time_student_id_dict:
            display_message += "✔️" + all_student_name_id_dict[student_id] + " checked in at " + on_time_student_id_dict[student_id] + "\n"
        
        display_message += "\n🅾️ THOSE WHO WERE ABSENT OR HAS A VALID REASON 🅾️\n\n"
        
        # Display those who have checked in late / VR / Absent
        for student_id in late_student_id_dict:
            if late_student_id_dict[student_id][0] == "VR":
                display_message += "⭕" + all_student_name_id_dict[student_id] + " has a valid reason: " + late_student_id_dict[student_id][1] + ".\n"
            else:
                display_message += "🔴" + all_student_name_id_dict[student_id] + " has been marked as Absent.\n"
        
        display_message += "\n✖️ THOSE WHO HAVE YET TO CHECK IN ✖️\n\n"
        unchecked_student_ids = []
        for student_id in all_student_name_id_dict:
            if student_id not in on_time_student_id_dict and student_id not in late_student_id_dict:
                unchecked_student_ids.append(student_id)
                display_message += "❌ " + all_student_name_id_dict[student_id] + "\n"
        
        bot.send_message(user_id,display_message) # display the attendance
        new_view_attendance.setUncheckedList(unchecked_student_ids)
        if len(unchecked_student_ids) > 0:
            bot.send_message(user_id,"Once your event or lesson is over, use /mark_late to edit the attendance of those who have yet to check in.")
            keyboard = [[types.InlineKeyboardButton("Yes",callback_data='sendReminder:yes'),types.InlineKeyboardButton("No",callback_data='sendReminder:no')]]
            markup = types.InlineKeyboardMarkup(keyboard)
            msg = bot.send_message(user_id,"Would you like me to send a reminder to these students for their reasoning?",reply_markup=markup)
            
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        new_view_attendance.del_view_attendance(user_id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "sendReminder")
def sendReminder(query):
    try:
        response = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        new_view_attendance = getViewAttendance(user_id)
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        if response == "no":
            bot.edit_message_text('Okay, we will not send the reminder. If you change your mind, just use /view_attendance again.',user_id,message_id)
            new_view_attendance.del_view_attendance(user_id)
        else:
            url = 'https://api.telegram.org/bot' + bot_token + '/sendMessage'
            for student_id in new_view_attendance.getUncheckedList():
                event_id = new_view_attendance.getEventId()
                section = new_view_attendance.getSection()
                event_name = Events.query.filter_by(event_id=event_id).first().event_name
                data = {'chat_id': student_id, 'text': 'Hi there, you are receiving this message because you have not checked in for ' + event_name + ' in ' + section + '. Please contact your TA / instructor and let them know of your reason. Failure to do so will result in your attendance being marked as Absent. Thank you!\n\n(P.S. Please do not reply to this bot)'}
                requests.post(url,data).json()
            bot.edit_message_text('Reminders have been sent out successfully, your students should be contacting you soon.',user_id,message_id)
            new_view_attendance.del_view_attendance(user_id)
            
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        new_view_attendance.del_view_attendance(user_id)

# ADMIN COMMAND TO MARK ATTENDANCE OF ABSENT OR LATE STUDENTS ##############################
@bot.message_handler(commands=['mark_late'])
def pickSection6(message):
    try:
        ongoing_action = doing_current_command(message.chat.id)
        if not ongoing_action:
            return
        admin_check = isAdmin(message.chat.id)
        if not admin_check:
            return
        section_list = retrieveSections(message.chat.id)
        markup = getSectionsMarkup(6,section_list,3)
        temp_mark_late = Temp_Mark_Late()
        temp_mark_late.add_mark_late(message.chat.id)
        bot.send_message(message.chat.id,'Please pick the section that you want to mark.',reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_mark_late.del_mark_late(message.chat.id)

@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "pickSection6")
def pickEventLate(query):
    try:
        section = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        temp_mark_late = getTempMarkLate(user_id)
        temp_mark_late.setSection(section)
        
        new_markup = types.InlineKeyboardMarkup([])
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
        events = Events.query.filter_by(section=section)
        row_limit = 4 # MODIFY IF REQUIRED
        keyboard = []
        row = []
        for event in events:
            row.append(types.InlineKeyboardButton(event.event_name,callback_data='pickEventLate:'+ str(event.event_id)))
            if len(row) >= row_limit:
                keyboard.append(row)
                row = []
        if len(row) > 0:
            keyboard.append(row)
        # If there are no events
        if len(keyboard) == 0:
            bot.edit_message_text("You have no events. Use /create to create a new one for your section.",user_id,message_id)
            temp_mark_late.del_mark_late(user_id)
            return
        bot.edit_message_text('You have chosen section '+ section +'.\n\nPick an event that you want to mark late attendance for.',user_id,message_id)
        markup = types.InlineKeyboardMarkup(keyboard)
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=markup)
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_mark_late.del_mark_late(user_id)
        
@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "pickEventLate")
def pickStudentsLate(query):
    event_id = query.data.split(":")[1]
    user_id = query.from_user.id
    message_id = query.message.id
    temp_mark_late = getTempMarkLate(user_id)
    temp_mark_late.setEventId(event_id)
    temp_mark_late.setOrigMessageId(message_id)
    new_markup = types.InlineKeyboardMarkup([])
    bot.edit_message_reply_markup(user_id,message_id,reply_markup=new_markup)
    try:
        # Retrieve students who havent checked in 
        all_students = User_Sections.query.filter_by(section=temp_mark_late.getSection(),role="Student")
        already_checked_in = Attendance.query.filter_by(event_id=event_id)
        already_late_recorded = Late_Attendance.query.filter_by(event_id=event_id)
        already_student_ids = []
        for s1 in already_checked_in:
            already_student_ids.append(s1.chat_id)
        for s3 in already_late_recorded:
            already_student_ids.append(s3.chat_id)
        all_student_ids = []
        for s2 in all_students:
            all_student_ids.append(s2.chat_id)
        
        # Displaying all students who havent checked in as INLINE MARKUP BUTTON
        keyboard = []
        row = []
        for chat_id in all_student_ids:
            if chat_id not in already_student_ids:
                student_user = Users.query.filter_by(chat_id=chat_id).first()
                callback = 'late_student:' + str(student_user.chat_id)
                row.append(types.InlineKeyboardButton(student_user.name,callback_data=callback))
                if len(row) == 4:
                    keyboard.append(row)
                    row = []
        if row != []:
            keyboard.append(row)
        # If no one is late (All-checked in)
        if keyboard == []:
            bot.edit_message_text('There are no students who were late for this event.',user_id,message_id)
            temp_mark_late.del_mark_late(user_id)
            return
        # If there are still late people
        keyboard.append([types.InlineKeyboardButton('Stop Marking',callback_data='late_student:StopMarking')])
        bot.edit_message_text('Click on the student whose late attendance you want to mark.\n\nClick on Stop Marking if you are done marking late attendance.',user_id,message_id)
        bot.edit_message_reply_markup(user_id,message_id,reply_markup=types.InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_mark_late.del_mark_late(user_id)
        
@bot.callback_query_handler(lambda query: query.data.split(":")[0] == "late_student")
def choose_status(query):  
    try:
        chat_id = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        temp_mark_late = getTempMarkLate(user_id)
        temp_mark_late.setChatId(chat_id)
        
        if chat_id == "StopMarking":
            # new_markup = types.InlineKeyboardMarkup([])
            bot.edit_message_text("You have stopped marking attendance for this section's event.",user_id,message_id)
            temp_mark_late.del_mark_late(user_id)
        else:
            markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton("Valid Reason (VR)",callback_data='statusUpdate:VR'),types.InlineKeyboardButton("Absent",callback_data='statusUpdate:Absent')]])
            student_name = Users.query.filter_by(chat_id=chat_id).first().name
            bot.edit_message_text('You have selected student, ' + student_name + '.\n\nWhat is his or her status?',user_id,message_id)
            bot.edit_message_reply_markup(user_id,message_id,reply_markup=markup)
            
    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_mark_late.del_mark_late(user_id)
        
@bot.callback_query_handler(lambda query: query.data.split(":")[0] == 'statusUpdate')
def updateStatus(query):
    try:
        status = query.data.split(":")[1]
        user_id = query.from_user.id
        message_id = query.message.id
        temp_mark_late = getTempMarkLate(user_id)
        temp_mark_late.setStatus(status)
        chat_id = temp_mark_late.getChatId()
        event_id = temp_mark_late.getEventId()
        student_name = Users.query.filter_by(chat_id=chat_id).first().name
        if status == "Absent":
            new_late_attendance = Late_Attendance(event_id=event_id,chat_id=chat_id,status=status,reason=None)
            db.session.add(new_late_attendance)
            db.session.commit()
            temp_mark_late.setStatus(None)
            temp_mark_late.setReason(None)
            new_keyboard = []
            row = []
            all_students = User_Sections.query.filter_by(section=temp_mark_late.getSection(),role="Student")
            already_checked_in = Attendance.query.filter_by(event_id=event_id)
            already_late_recorded = Late_Attendance.query.filter_by(event_id=event_id)
            already_student_ids = []
            for s1 in already_checked_in:
                already_student_ids.append(s1.chat_id)
            for s3 in already_late_recorded:
                already_student_ids.append(s3.chat_id)
            all_student_ids = []
            for s2 in all_students:
                all_student_ids.append(s2.chat_id)
            for chat_id in all_student_ids:
                if chat_id not in already_student_ids:
                    student_user = Users.query.filter_by(chat_id=chat_id).first()
                    callback = 'late_student:' + str(student_user.chat_id)
                    row.append(types.InlineKeyboardButton(student_user.name,callback_data=callback))
                    if len(row) == 4:
                        new_keyboard.append(row)
                        row = []
            if row != []:
                new_keyboard.append(row)
                
            display_message = 'You have successfully marked ' + student_name + "as Absent.\n\n"
            if new_keyboard == []:
                display_message += "There are no more students left to mark."
                temp_mark_late.del_mark_late(user_id)
            else:
                new_keyboard.append([types.InlineKeyboardButton('Stop Marking',callback_data='late_student:StopMarking')])
                display_message += "Which student do you want to mark next?"

            bot.edit_message_text(display_message,user_id,message_id)
            if new_keyboard != []:
                bot.edit_message_reply_markup(user_id,message_id,reply_markup=types.InlineKeyboardMarkup(new_keyboard))
        else:
            msg = bot.edit_message_text('Please enter a valid reason for ' + student_name + "'s absence in the next chat bubble. Keep it less than 100 characters long.",user_id,message_id)
            bot.register_next_step_handler(msg,addReason)

    except Exception as e:
        bot.send_message(query.from_user.id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_mark_late.del_mark_late(user_id)

def addReason(message):
    reason = message.text
    user_id = message.chat.id
    temp_mark_late = getTempMarkLate(user_id)
    event_id = temp_mark_late.getEventId()
    try:
        if len(reason) > 100:
            msg = bot.reply_to(message,"Your reason is too long, please keep it to less than 100 characters leh.\n\nEnter your reason again!")
            bot.register_next_step_handler(msg,addReason)
            return
        else:
            chat_id = temp_mark_late.getChatId()
            student_name = Users.query.filter_by(chat_id=chat_id).first().name
            new_late_attendance = Late_Attendance(event_id=event_id,chat_id=chat_id,status=temp_mark_late.getStatus(),reason=reason)
            db.session.add(new_late_attendance)
            db.session.commit()
            bot.delete_message(chat_id=user_id,message_id=temp_mark_late.getOrigMessageId())
            temp_mark_late.setOrigMessageId(None)
        temp_mark_late.setStatus(None)
        temp_mark_late.setReason(None)
        new_keyboard = []
        row = []
        all_students = User_Sections.query.filter_by(section=temp_mark_late.getSection(),role="Student")
        already_checked_in = Attendance.query.filter_by(event_id=event_id)
        already_late_recorded = Late_Attendance.query.filter_by(event_id=event_id)
        already_student_ids = []
        for s1 in already_checked_in:
            already_student_ids.append(s1.chat_id)
        for s3 in already_late_recorded:
            already_student_ids.append(s3.chat_id)
        all_student_ids = []
        for s2 in all_students:
            all_student_ids.append(s2.chat_id)
        for chat_id in all_student_ids:
            if chat_id not in already_student_ids:
                student_user = Users.query.filter_by(chat_id=chat_id).first()
                callback = 'late_student:' + str(student_user.chat_id)
                row.append(types.InlineKeyboardButton(student_user.name,callback_data=callback))
                if len(row) == 4:
                    new_keyboard.append(row)
                    row = []
        if row != []:
            new_keyboard.append(row)
            
        display_message = 'You have successfully marked ' + student_name + ' as VR with reason: ' + reason + ".\n\n"
        if new_keyboard == []:
            display_message += "There are no more students left to mark."
            temp_mark_late.del_mark_late(user_id)
        else:
            new_keyboard.append([types.InlineKeyboardButton('Stop Marking',callback_data='late_student:StopMarking')])
            display_message += "Which student do you want to mark next?"
            
        bot.send_message(user_id,display_message,reply_markup=types.InlineKeyboardMarkup(new_keyboard))
            
    except Exception as e:
        bot.send_message(user_id,"An error occurred: " + str(e) + ". Please contact your instructor or notify the developer.")
        temp_mark_late.del_mark_late(user_id)
while True:
    try:
        bot.polling()
    except Exception:
        time.sleep(15)