import pandas as pd
import datetime
import pickledb
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.ext.dispatcher import run_async
from operator import itemgetter, attrgetter
import re
from summa import keywords
import socketio
import sys

keys = ["1013409242:AAGaI2W0HqxRoR-eD33gvxTE1NQmBHMW2PQ",
		"940954250:AAGPtSL2d5VXwgTwP4A6laOHwY-50s5BuGk",
		"1016988681:AAGrA3QKlWaYf1D2a6Xpdkgn21fXEM1vXHI",
		"1016225307:AAFBNxjXPbSyQwOVwaP9KoWkMxMgrNcq_F8",
		"1046961279:AAGGEmVaPrBwXe16bb2ypECG_eydDXrv-bQ",
		"928958539:AAEy8H53pu3aU7GOUCJvojQXmau1N_qarz8"]

print("select bot # here:")
print("1. Poki")
print("2. Mrs. Poki")
print("3. Ms. Poki")
print("4. Mr. Poki Young")
print("5. Mr. Poki Old")
print("6. Dr. Poki")
index = int(input()) - 1 
APIKey = keys[index]
print("ok, watching # " + str( index + 1) )
print("what should the filename of the results be? example: bot1.db:")
filename = input() 
print("outputting to " + filename)

BOTNAME = 'poki_en_bot'

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)
logger = logging.getLogger(__name__)

# Database
db = pickledb.load(filename, True)

if not db.get('chats'):
	db.set('chats', [])
print("DB Loaded.")

# RegEx
timeRegEx = re.compile('\d+\D')
print("RegEx Setup.")

# Global Variables

timeUnitDict = {1: 'minute', 60: 'hour', 1440: 'day'}

# Group Intro

def groupchatIntro(update, context):
	if update.message['group_chat_created']: # Group Chat Started.
		chat_id = update.message.chat_id
		chatDBInitialize(chat_id)
		
		response = "Hi! I'm Poki, a chatbot for your group discussion. I provide three features.\n"
		response += "1. Manage discussion time.\n"
		response += "2. Tell about members' participation status.\n"
		response += "3. Summarize each member's and overall group's opinions. "
		context.bot.send_message(chat_id, text=response, timeout=7200)
	
		response = "I provide the above information in the middle and after the discussion.💡"
		context.bot.send_message(chat_id, text=response, timeout=7200)

		response = "Type /go to start a discussion and set the time. You can end the "
		response += "discussion with the /end command."
		context.bot.send_message(chat_id, text=response, timeout=7200)

		response = "⏰You can check the remaining time via the /time command!"
		context.bot.send_message(chat_id, text=response, timeout=7200)

		response = "I have to list up the members before you start! Everyone please answer “Yes”"
		context.bot.send_message(chat_id, text=response, timeout=7200)

# Button Handlers

def button(update, context):
	query = update.callback_query
	chat_id = query.message.chat_id
	if query.data == "dabateNameYes":
		response = "YES ⭕"
		query.edit_message_text(text=response)
		inputDebateTime(context, chat_id)
	elif query.data == "dabateNameNo":
		response = "NO ❌"
		query.edit_message_text(text=response)
		inputDebateName(context, chat_id)
	elif query.data == "dabateTimeYes":
		response = "YES ⭕"
		query.edit_message_text(text=response)
		
		db.set(f"{chat_id}_waitingStatus", "")
		db.set(f"{chat_id}_settingFinished", True)

		debateName = db.get(f"{chat_id}_debateName")
		debateTime = db.get(f"{chat_id}_debateTime")
		debateTimeUnitValid = db.get(f"{chat_id}_debateTimeUnitValid")
		debateTimeUnit = timeUnitDict[debateTimeUnitValid]

		timeSingular = 's'
		if debateTime == 1:
			timeSingular = ''
		response = f"Let's have a discussion about {debateName} for {debateTime} {debateTimeUnit}{timeSingular}"
		context.bot.send_message(chat_id, text=response, timeout=7200)
		response = "If the discussion ends earlier than expected, please manually end it with the /end command."
		context.bot.send_message(chat_id, text=response, timeout=7200)

		totalTime = debateTime * 60 * debateTimeUnitValid
		lastTime = 10
		if totalTime < 120: # ~2 Min
			lastTime = 10
		elif totalTime < 600: # 2~10 Min
			lastTime = 60
		elif totalTime < 900: # 10~15 Min
			lastTime = 120
		elif totalTime < 1800: # 15~30 Min
			lastTime = 300
		elif totalTime < 7200: # 30~120 Min
			lastTime = 600
		else: # 120 Min ~
			lastTime = int(totalTime/5/60)*60
		introTime = totalTime/2
		middleTime = introTime - lastTime

		debateEndTimeSet(chat_id, totalTime)

		db.set(f"{chat_id}_debateStatus", "INTRO")
		db.set(f"{chat_id}_totalTime", totalTime)
		db.set(f"{chat_id}_introTime", introTime)
		db.set(f"{chat_id}_middleTime", middleTime)
		db.set(f"{chat_id}_lastTime", lastTime)
		context.chat_data['job_debateOn'] = context.job_queue.run_once(debateIntro, introTime, context=chat_id)
	elif query.data == "dabateTimeNo":
		response = "NO ❌"
		query.edit_message_text(text=response)
		inputDebateTime(context, chat_id)
	elif query.data == "dabateFinishedYes":
		response = "YES ⭕"
		query.edit_message_text(text=response)
		response = "✏️Please write the final consensus."
		context.bot.send_message(chat_id, text=response, timeout=7200)
		db.set(f"{chat_id}_waitingStatus", "CONCLUSION")
	elif query.data == "dabateFinishedNo":
		response = "NO ❌"
		query.edit_message_text(text=response)
		finishConclusion(context, chat_id, False)
	elif query.data == "dabateEndYes":
		response = "YES ⭕"
		query.edit_message_text(text=response)

		job = context.chat_data['job_debateOn']
		job.schedule_removal()
		del context.chat_data['job_debateOn']
			
		context.job_queue.run_once(debateFinished, 1, context=chat_id)
	elif query.data == "dabateEndNo":
		response = "NO ❌"
		query.edit_message_text(text=response)
		## REMAIN TIME
		sendTimeLeft(context, chat_id)

	else:
		print("else in button")

# Command Handlers

# Start Debate (command: /go)
def debateGo(update, context):
	chat_id = update.message.chat_id
	debateStarted = db.get(f"{chat_id}_debateStarted")
	if debateStarted:
		#print("Already Started.")
		response = "❗The discussion is already in progress. If you want to start a new discussion, please end the existing discussion with the /end command!"
		context.bot.send_message(chat_id, text=response, timeout=7200)
	else:
		debateInitialize(chat_id)
		db.set(f"{chat_id}_debateStatus", "Setting")
		inputDebateName(context, chat_id)

# End Debate (command: /end)
def debateEnd(update, context):
	chat_id = update.message.chat_id
	debateStarted = db.get(f"{chat_id}_debateStarted")
	if not debateStarted:
		print("Debate Not Started.")
	else:
		## To Button
		response = f"❗Do you really want to end the discussion?"
		keyboard = [[InlineKeyboardButton("YES ⭕", callback_data='dabateEndYes'),
					InlineKeyboardButton("NO ❌", callback_data='dabateEndNo')]]
		reply_markup = InlineKeyboardMarkup(keyboard)
		context.bot.send_message(chat_id, text=response, reply_markup=reply_markup, timeout=7200)

# Check The Remaining Time (command: /time)
def debateTime(update, context):
	chat_id = update.message.chat_id
	debateStarted = db.get(f"{chat_id}_debateStarted")
	if debateStarted:
		sendTimeLeft(context, chat_id)
		
def reset(update, context):
	groupchatIntro(update, context)

def error(update, context):
	"""Log Errors caused by Updates."""
	logger.warning('Update "%s" caused error "%s"', update, context.error)

# Message Handlers

def getMessage(update, context):
	print("Get Message")
	chat_id = update.message.chat_id
	userIDs = db.get(f"{chat_id}_userIDs")
	debateStarted = db.get(f"{chat_id}_debateStarted")
	settingFinished = db.get(f"{chat_id}_settingFinished")
	talkingUsersTOTAL = db.get(f"{chat_id}_talkingUsersTOTAL")
	waitingStatus = db.get(f"{chat_id}_waitingStatus") #NAME	

	user = update.message.from_user
	userFirstName = user['first_name']
	userLastName = user['last_name']
	userName = userFirstName
	text = update.message.text

	if userLastName:
		userName += f" {userLastName}"
	userID = user['id']

	# User Initialization
	if userID not in userIDs:
		userIDs.append(userID)
		db.set(f"{chat_id}_userIDs", userIDs)
		db.set(f"{chat_id}_{userID}_userName", userName)
		db.set(f"{chat_id}_{userID}_userMsgTOTAL", "")
		db.set(f"{chat_id}_{userID}_userMsgINTRO", "")
		db.set(f"{chat_id}_{userID}_userMsgMIDDLE", "")

	# Debate Name Setting
	if waitingStatus == 'NAME':
		db.set(f"{chat_id}_debateName", text)
		response = f"❓Your discussion is about {text}?"
		keyboard = [[InlineKeyboardButton("YES ⭕", callback_data='dabateNameYes'),
					InlineKeyboardButton("NO ❌", callback_data='dabateNameNo')]]
		reply_markup = InlineKeyboardMarkup(keyboard)
		context.bot.send_message(chat_id, text=response, reply_markup=reply_markup, timeout=7200)

	# Debate Time Setting
	if waitingStatus == 'TIME':
		regExSearch = timeRegEx.search(text)
		validResponse = False
		if regExSearch:
			result = regExSearch.group()
			strtime = result[0:-1]
			time = int(strtime)
			unit = result[-1]
			timeValid = (time > 0) & (time < 1000)
			unitMin = ['m', 'M', '분']
			unitHour = ['h', 'H', '시']
			unitDay = ['d', 'D', '일']
			#timeUnitDict = {1: '분', 60: '시간', 1440: '일'}
			unitValid = False
			if unit in unitMin:
				unitValid = 1
			elif unit in unitHour:
				unitValid = 60
			elif unit in unitDay:
				unitValid = 1440
			validResponse = bool(regExSearch) & bool(timeValid) & bool(unitValid)
			if validResponse:
				db.set(f"{chat_id}_debateTime", time)
				db.set(f"{chat_id}_debateTimeUnitValid", unitValid)
				timeSingular = 's'
				if time == 1:
					timeSingular = ''
				response = f"❓The discussion will be held for {time} {timeUnitDict[unitValid]}{timeSingular}?"
				keyboard = [[InlineKeyboardButton("YES ⭕", callback_data='dabateTimeYes'),
							InlineKeyboardButton("NO ❌", callback_data='dabateTimeNo')]]
				reply_markup = InlineKeyboardMarkup(keyboard)
				context.bot.send_message(chat_id, text=response, reply_markup=reply_markup, timeout=7200)
		if not validResponse:
			response = "⏰Please write in the form of “30m” or “5h” or “1d” according to minutes, hours and days. If you are discussing for 30 minutes, please enter “30m”."
			context.bot.send_message(chat_id, text=response, timeout=7200)

	# Debate Conclusion Setting
	if waitingStatus == 'CONCLUSION':
		db.set(f"{chat_id}_waitingStatus", "")
		db.set(f"{chat_id}_debateConclusion", text)
		finishConclusion(context, chat_id, True)

	# Check talking User in Debate.
	if debateStarted & settingFinished:
		if userID not in talkingUsersTOTAL:
			talkingUsersTOTAL.append(userID)
			db.set(f"{chat_id}_talkingUsersTOTAL", talkingUsersTOTAL)
		debateStatus = db.get(f"{chat_id}_debateStatus")
		if debateStatus == 'INTRO':
			talkingUsersINTRO = db.get(f"{chat_id}_talkingUsersINTRO")
			if userID not in talkingUsersINTRO:
				talkingUsersINTRO.append(userID)
				db.set(f"{chat_id}_talkingUsersINTRO", talkingUsersINTRO)
			userMsgIntro = db.get(f"{chat_id}_{userID}_userMsgINTRO")
			userMsg = db.get(f"{chat_id}_{userID}_userMsgTOTAL")
			userMsgIntro += f" {text}."
			userMsg += f" {text}."
			db.set(f"{chat_id}_{userID}_userMsgINTRO", userMsgIntro)
			db.set(f"{chat_id}_{userID}_userMsgTOTAL", userMsg)
		elif debateStatus == 'MIDDLE':
			talkingUsersMIDDLE = db.get(f"{chat_id}_talkingUsersMIDDLE")
			if userID not in talkingUsersMIDDLE:
				talkingUsersMIDDLE.append(userID)
				db.set(f"{chat_id}_talkingUsersMIDDLE", talkingUsersMIDDLE)
			userMsgMiddle = db.get(f"{chat_id}_{userID}_userMsgMIDDLE")
			userMsg = db.get(f"{chat_id}_{userID}_userMsgTOTAL")
			userMsgMiddle += f" {text}."
			userMsg += f" {text}."
			db.set(f"{chat_id}_{userID}_userMsgMIDDLE", userMsgMiddle)
			db.set(f"{chat_id}_{userID}_userMsgTOTAL", userMsg)
		elif debateStatus == 'LAST':
			userMsg = db.get(f"{chat_id}_{userID}_userMsgTOTAL")
			userMsg += f" {text}."
			db.set(f"{chat_id}_{userID}_userMsgTOTAL", userMsg)
		saveMessage(chat_id, user_id=userID, message=text)


# Methods

	#Initialize

def chatDBInitialize(chat_id):
	db.set(f"{chat_id}_userIDs", [])
	db.set(f"{chat_id}_talkingUsersTOTAL", [])
	db.set(f"{chat_id}_talkingUsersINTRO", [])
	db.set(f"{chat_id}_talkingUsersMIDDLE", [])
	db.set(f"{chat_id}_debateStarted", False)
	db.set(f"{chat_id}_settingFinished", False)

	data = {
		'chat_id': [],
		'debateStatus':[],
		'user_id': [],
		'userName': [],
		'message': [],
		'timestamp': [],
	}

	pd_msg = pd.DataFrame(data)
	filename = f"msg_{chat_id}"
	pd_msg.to_csv(f"log/{filename}.csv", mode = 'w')

def debateInitialize(chat_id):
	userIDs = db.get(f"{chat_id}_userIDs")
	for userID in userIDs:
		db.set(f"{chat_id}_{userID}_userMsgTOTAL", "")
		db.set(f"{chat_id}_{userID}_userMsgINTRO", "")
		db.set(f"{chat_id}_{userID}_userMsgMIDDLE", "")
	db.set(f"{chat_id}_talkingUsersTOTAL", [])
	db.set(f"{chat_id}_talkingUsersINTRO", [])
	db.set(f"{chat_id}_talkingUsersMIDDLE", [])
	db.set(f"{chat_id}_debateStarted", True)
	db.set(f"{chat_id}_settingFinished", False)
	db.set(f"{chat_id}_waitingStatus", "")
	db.set(f"{chat_id}_debateName", "")
	db.set(f"{chat_id}_debateTime", 0)
	db.set(f"{chat_id}_debateTimeUnit", 1)

	db.set(f"{chat_id}_totalTime", 0)
	db.set(f"{chat_id}_introTime", 0)
	db.set(f"{chat_id}_middleTime", 0)
	db.set(f"{chat_id}_lastTime", 0)

	db.set(f"{chat_id}_debateStatus", "SETTING")

	db.set(f"{chat_id}_debateConclusion", "")
	

	# Dabate Setting


def inputDebateName(context, chat_id):
	db.set(f"{chat_id}_waitingStatus", "NAME")	
	response = "✏️Write a discussion topic"
	context.bot.send_message(chat_id, text=response, timeout=7200)

def inputDebateTime(context, chat_id):
	db.set(f"{chat_id}_waitingStatus", "TIME")	
	response = "⏰Please set the discussion time.\n"
	response += "Write in “30m” or “5h” or “1d” depending on the minute, hour and day."
	context.bot.send_message(chat_id, text=response, timeout=7200)


	# On Debate


def debateIntro(context):
	job = context.job
	chat_id = job.context
	chat_data = context._dispatcher.chat_data

	response = "Half way over!"
	context.bot.send_message(chat_id, text=response, timeout=7200)

	sendResponseFiveSummary(context, 'INTRO')

	## ADD IN en
	response = "If the discussion ends earlier than expected, please manually end it with the /end command. 😎"
	context.bot.send_message(chat_id, text=response, timeout=7200)

	askToNotTalkingMember(context, 'INTRO')
	db.set(f"{chat_id}_debateStatus", "MIDDLE")

	middleTime = db.get(f"{chat_id}_middleTime")
	chat_data['job_debateOn'] = context.job_queue.run_once(debateMiddle, middleTime, context=chat_id)

def debateMiddle(context):
	job = context.job
	chat_id = job.context
	chat_data = context._dispatcher.chat_data

	middleTime = db.get(f"{chat_id}_middleTime")
	lastTime = db.get(f"{chat_id}_lastTime")

	day = int(lastTime / 86400)
	t = lastTime % 86400
	hour = int(t / 3600)
	t = t % 3600
	minute = int(t / 60)
	t = t % 60
	second = int(t)
	
	timeStrings = []
	
	if day:
		timeSingular = ''
		if day > 1:
			timeSingular = 's'
		timeStrings.append(f"{day} day{timeSingular}")
	if hour:
		timeSingular = ''
		if hour > 1:
			timeSingular = 's'
		timeStrings.append(f"{hour} hour{timeSingular}")
	if minute:
		timeSingular = ''
		if minute > 1:
			timeSingular = 's'
		timeStrings.append(f"{minute} minute{timeSingular}")
	if second:
		timeSingular = ''
		if second > 1:
			timeSingular = 's'
		timeStrings.append(f"{second} second{timeSingular}")

	timeStr = ' '.join(timeStrings)

	response = f"⏰ {timeStr} left for discussion! "
	context.bot.send_message(chat_id, text=response, timeout=7200)

	sendResponseFiveSummary(context, 'MIDDLE')
	db.set(f"{chat_id}_debateStatus", "LAST")

	lastTime = db.get(f"{chat_id}_lastTime")
	chat_data['job_debateOn'] = context.job_queue.run_once(debateFinished, lastTime, context=chat_id)

	# End Debate

def debateFinished(context):
	job = context.job
	chat_id = job.context

	db.set(f"{chat_id}_debateStarted", False)

	response = "Time is up!"
	context.bot.send_message(chat_id, text=response, timeout=7200)
	
	response = "Here is the overall information for the discussion. "
	context.bot.send_message(chat_id, text=response, timeout=7200)

	sendResponseFiveSummary(context, 'TOTAL')

	response = "Would you like to organize the discussion by writing the final consensus?"
	keyboard = [[InlineKeyboardButton("YES ⭕", callback_data='dabateFinishedYes'),
				InlineKeyboardButton("NO ❌", callback_data='dabateFinishedNo')]]
	reply_markup = InlineKeyboardMarkup(keyboard)
	context.bot.send_message(chat_id, text=response, reply_markup=reply_markup, timeout=7200)


	# Summarize


def sendResponseFiveSummary(context, status):
	job = context.job
	chat_id = job.context

	response = responseTalkingMemeberList(chat_id, status)
	context.bot.send_message(chat_id, text=response, timeout=7200)

	response = responseNotTalkingMemberList(chat_id, status)
	context.bot.send_message(chat_id, text=response, timeout=7200)

	response = responseTalkingRank(chat_id, status)
	context.bot.send_message(chat_id, text=response, timeout=7200)

	response = responseMembersKeywords(chat_id, status)
	context.bot.send_message(chat_id, text=response, timeout=7200)

	response = responseOverallKeywords(chat_id, status)
	context.bot.send_message(chat_id, text=response, timeout=7200)



def responseTalkingMemeberList(chat_id, status):
	response = "🔹Participants\n"
	talkingUsers = db.get(f"{chat_id}_talkingUsers{status}")
	for userID in talkingUsers:
		userName = db.get(f"{chat_id}_{userID}_userName")
		response += f" - {userName}\n"
	return response


def responseNotTalkingMemberList(chat_id, status):
	response = "🔹Non-participants\n"
	userIDs = db.get(f"{chat_id}_userIDs")
	talkingUsers = db.get(f"{chat_id}_talkingUsers{status}")
	for userID in userIDs:
		if userID not in talkingUsers:
			userName = db.get(f"{chat_id}_{userID}_userName")
			response += f" - {userName}\n"
	return response

def responseTalkingRank(chat_id, status):
	response = "🔹Participation ranking\n"
	talkingUsers = db.get(f"{chat_id}_talkingUsers{status}")
	debateRanking = []
	for userID in talkingUsers:
		userName = db.get(f"{chat_id}_{userID}_userName")
		userMsgLen = len(db.get(f"{chat_id}_{userID}_userMsg{status}"))
		debateRanking.append([userName, userMsgLen])
	debateRanking.sort(key=lambda x: x[1], reverse=True)
	for rank in debateRanking:
		response += f" - {rank[0]}\n"
	return response

def responseMembersKeywords(chat_id, status):
	response = "🔹Keyword per member\n"
	talkingUsers = db.get(f"{chat_id}_talkingUsers{status}")
	for userID in talkingUsers:
		userName = db.get(f"{chat_id}_{userID}_userName")
		userMsg = db.get(f"{chat_id}_{userID}_userMsg{status}")
		keywords = keywordExtractEN(userMsg)
		print("this user's messages are:", userMsg)
		response += f" {userName}: {keywords}\n"
	return response

def keywordExtractEN(text):
	parsedList = keywords.keywords(text)
	keywordList = parsedList.replace(' ', '').split('\n')
	if(len(parsedList) < 1):
		return "No keywords detected."
	hashtags = map(lambda x: f"#{x}", keywordList)
	return ' '.join(hashtags)

def responseOverallKeywords(chat_id, status):
	response = "🔹Overall keyword\n"
	talkingUsers = db.get(f"{chat_id}_talkingUsers{status}")
	overallMsg = ""
	for userID in talkingUsers:
		overallMsg += db.get(f"{chat_id}_{userID}_userMsg{status}")
	keywords = keywordExtractEN(overallMsg)
	response += keywords
	return response

def askToNotTalkingMember(context, status):
	job = context.job
	chat_id = job.context
	response = responseAskToNotTalkingMember(chat_id, status)
	if response:
		context.bot.send_message(chat_id, text=response, timeout=7200)

def responseAskToNotTalkingMember(chat_id, status):
	userIDs = db.get(f"{chat_id}_userIDs")
	print(f'chat_id: {chat_id}')
	print(f'userIDs: {userIDs}')
	talkingUsers = db.get(f"{chat_id}_talkingUsers{status}")
	notTalkingUsers = []
	for userID in userIDs:
		if userID not in talkingUsers:
			userName = db.get(f"{chat_id}_{userID}_userName")
			notTalkingUsers.append(userName)
	
	if notTalkingUsers:
		notTalkingUsersStr = ', '.join(notTalkingUsers)
		response = f'What is {notTalkingUsersStr}’s opinion?'
		return response
	return False

def finishConclusion(context, chat_id, withConclusion):
	debateName = db.get(f"{chat_id}_debateName")
	debateTime = db.get(f"{chat_id}_debateTime")
	debateTimeUnitValid = db.get(f"{chat_id}_debateTimeUnitValid")
	debateTimeUnit = timeUnitDict[debateTimeUnitValid]
	debateConclusion = db.get(f"{chat_id}_debateConclusion")
	timeSingular = ''
	if debateTime > 1:
		timeSingular = 's'

	response = "Discussion Log\n"
	response += f"🔹Topic: {debateName}\n"
	response += f"🔹Time: {debateTime} {debateTimeUnit}{timeSingular}\n"
	
	if withConclusion:
		response += f"➖Consensus: {debateConclusion}"

	context.bot.send_message(chat_id, text=response, timeout=7200)

def saveMessage(chat_id, user_id, message, answer=False):
	teamCode = db.get(f"{chat_id}_teamCode")
	debateStatus = db.get(f"{chat_id}_debateStatus")
	if answer:
		debateStatus = "ANSWER"
	data = {
		'chat_id': [chat_id],
		'debateStatus':[debateStatus],
		'user_id': [user_id],
		'userName': [db.get(f"{user_id}_userName")],
		'message': [message],
		'timestamp': [datetime.datetime.today().ctime()],
	}
	pd_msg = pd.DataFrame(data)
	filename = f"msg_{chat_id}"
	pd_msg.to_csv(f"log/{filename}.csv", mode = 'a', header=False)

def debateEndTimeSet(chat_id, totalTime):
	days = int(totalTime/86400)
	seconds = int(totalTime%86400)
	timeNow = datetime.datetime.now()
	debateTime = datetime.timedelta(days = days, seconds = seconds)
	debateEndAt = timeToString(timeNow + debateTime)
	db.set(f"{chat_id}_debateEndAt", debateEndAt)

def sendTimeLeft(context, chat_id):
	timeNow = datetime.datetime.now()
	debateEndAt = stringToTime(db.get(f"{chat_id}_debateEndAt"))
	debateTimeLeft = debateEndAt - timeNow
	debateTimeLeftDays = debateTimeLeft.days
	debateTimeLeftSeconds = debateTimeLeft.seconds
	debateTimeLeftHours = int(debateTimeLeftSeconds/3600)
	debateTimeLeftMinutes = int((debateTimeLeftSeconds%3600)/60)
	debateTimeLeftSeconds = int(debateTimeLeftSeconds%60)
	
	timeLeftStrings = []
	if debateTimeLeftDays > 0:
		days = f'{debateTimeLeftDays} day'
		if debateTimeLeftDays > 1:
			days += 's'
		timeLeftStrings.append(days)
	if debateTimeLeftHours > 0:
		hours = f'{debateTimeLeftHours} hour'
		if debateTimeLeftHours > 1:
			hours += 's'
		timeLeftStrings.append(hours)
	if debateTimeLeftMinutes > 0:
		minutes = f'{debateTimeLeftMinutes} minute'
		if debateTimeLeftMinutes > 1:
			minutes += 's'
		timeLeftStrings.append(minutes)
	if debateTimeLeftSeconds > 0:
		seconds = f'{debateTimeLeftSeconds} second'
		if debateTimeLeftSeconds > 1:
			seconds += 's'
		timeLeftStrings.append(seconds)

	timeLeftString = ' '.join(timeLeftStrings)
	
	response = f"{timeLeftString} left. You can finish with the /end"
	context.bot.send_message(chat_id, text=response, timeout=7200)
	
def timeToString(dt):
	return dt.isoformat()

def stringToTime(time_str):
	return datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")


async def main():
	updater = Updater(APIKey, use_context=True)
	dp = updater.dispatcher

	# CallbackQuery Handler
	dp.add_handler(CallbackQueryHandler(button))

	# Command Handler
	dp.add_handler(CommandHandler("Go", debateGo))
	dp.add_handler(CommandHandler("End", debateEnd))
	dp.add_handler(CommandHandler("Time", debateTime))
	
	# Message Handler
	dp.add_handler(MessageHandler(Filters.status_update, groupchatIntro,
									pass_job_queue=True,
									pass_chat_data=True))
	dp.add_handler(MessageHandler(Filters.text, getMessage,
								  pass_job_queue=True,
								  pass_chat_data=True))

	# log all errors
	dp.add_error_handler(error)
	print("POKI EN CHATBOT")
	print("Dispatcher all set up.")
	updater.start_polling()
	updater.idle()

# def sigterm_handler(_signo, _stack_frame):
#     # Raises SystemExit(0):
# 	sio.emit("exiting")
#     sys.exit(0)

# if sys.argv[1] == "handle_signal":
#     signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == '__main__':
	main()
	sio = socketio.Client()
	sio.connect('http://localhost:1234')
	print('my sid is', sio.sid)
	sio.emit('running', str(index))