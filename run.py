#!/usr/bin/env python
# Requires: twitter, requests, requests-oauthlib, sqlite3

"""
TODO
-----------
2. Write a README (see the Stats project) that indicates to users how to create their own bot and maybe a design doc?
"""

"""
TESTING ARGVS
- notweet = doesn't tweet nor record the usage of the tweet on the database.
- badcredentials = ensures that the credentails are incorrect.
"""

# main dependencies
import twitter
import sqlite3
import sys
import textwrap

# internal dependencies
import credentials
from systemlog import logger

# constants
SQLDB = 'facts.db'
factsTable = 'facts'
twitterCharacterLimit = 280
tweetSeparator = '...'


def getRandomMessage():
	""" Chooses a random message, prioritizing messages that have been posted the least in the past. """
	try:
		with sqlite3.connect(SQLDB) as database:
			(rowID, addedDate, category, message, source, media, usedCount) = database.cursor().execute('SELECT * FROM {} ORDER BY usedCount, RANDOM() DESC limit 1'.format(factsTable)).fetchone()
			logger.info('===============\n1/4 - Retrieval successful: {} {}\n==============='.format(message, media))
	except:
		logger.critical('===============\n1/4 - Retrieval failed. Unable to retrieve a message from the DB. Notifying over email.\n===============')
		return None
	return (rowID, message, media, usedCount)


def connnectToTwitter():
	""" Connects to Twitter. Uses the Credentials file to isolate credentials from the main running script. """
	
	if 'badcredentials' in sys.argv:
		logger.info('2/4 - Using intentionally bad credentials.')
		credentials.consumer_key = 'fake'

	try:
		api = twitter.Api(
			consumer_key=credentials.consumer_key,
			consumer_secret=credentials.consumer_secret,
			access_token_key=credentials.access_token_key,
			access_token_secret=credentials.access_token_secret
			)
		api.VerifyCredentials()  # Generates error if log in didn't work
		logger.info('2/4 - Successfully logged into Twitter.\n===============')
	except Exception as e:
		logger.critical('2/4 - Couldn\'t log into Twitter: {}. Notifying over email.\n==============='.format(str(e.message)))
		return None
	return api


def tweet(message, api, media=None):
	""" Tweets the message. The first tweet carries the image, if any. Following tweets are appended in order if the message length exceeds Twitter's character limit. """

	if 'notweet' in sys.argv:
		logger.info('3/4 - Skipping Tweet.')
		return True

	try:
		messages = textwrap.wrap(message, width=twitterCharacterLimit)
		if len(messages) == 1:
			# Carries the image and no tweet separator
			response = api.PostUpdate(status=messages[0], media=media)
			logger.info('3/4 - Tweet ID {} sent successfully.'.format(str(response.id)))
		elif len(messages) > 1:
			# Since multiple tweets are needed, we re-chunk the message to allow for the tweet separator, except in the last message.
			messages = textwrap.wrap(message, width=twitterCharacterLimit - len(tweetSeparator))
			response = api.PostUpdate(status=messages[0] + tweetSeparator, media=media)
			logger.info('3/4 - Tweet ID {} sent successfully.'.format(str(response.id)))
			for message in messages[1:-1]:
				response = api.PostUpdate(status=message + tweetSeparator, in_reply_to_status_id=response.id)
				logger.info('3/4 - Tweet ID {} sent successfully.'.format(str(response.id)))
			response = api.PostUpdate(status=messages[-1], in_reply_to_status_id=response.id)
			logger.info('3/4 - Tweet ID {} sent successfully.'.format(str(response.id)))
		logger.info('===============')

	except Exception as e:
		logger.critical('3/4 - Couldn\'t send the Tweet(s): {}. Notifying over email.\n==============='.format(str(e.message)))
		return None
	return True


def markUsed(rowID, usedCount):
	""" Marks messages as used, helping prevent message duplication when posting. """

	if 'notweet' in sys.argv:
		logger.info('4/4 - Skipping writing to the DB.')
		return True

	try:
		with sqlite3.connect(SQLDB) as database:
			cursor = database.cursor()
			cursor.execute('UPDATE {} SET usedCount = {} WHERE rowID = {}'.format(factsTable, usedCount, rowID))
			database.commit()
			logger.info('4/4 - Write successful. Message ID {} updated to {} uses.\n==============='.format(str(rowID), str(usedCount)))
	except Exception as e:
		logger.critical('4/4 - Writing failed: {}. Notifying over email.\n==============='.format(e))
		return None
	return


def main():
	global api, message
	(rowID, message, media, usedCount) = getRandomMessage()
	if message:
		api = connnectToTwitter()
		if api:
			result = tweet(message, api, media)
			if result:
				markUsed(rowID, usedCount + 1)
	return


main()
