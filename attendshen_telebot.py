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
        # command is either 'complete' or 'delete
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
        add_current_command(chat_id,"deleteStu")
    def del_temp_student(self,chat_id):
        del temp_student_dict[chat_id]
        end_current_command(chat_id)

        

def getTempEnroll(chat_id):
    return temp_enroll_dict[chat_id]

def getTempCreateEvent(chat_id):
    return temp_create_event_dict[chat_id]

def getTempModifyEvent(chat_id):
    return temp_modify_event_dict[chat_id]

def getTempStudent(chat_id):
    return temp_student_dict[chat_id]

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
@bot.message_handler(commands=['deleteStudent'])
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

# FINISH delete student callback
while True:
    try:
        bot.polling()
    except Exception:
        time.sleep(15)