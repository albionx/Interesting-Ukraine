#!/usr/bin/env python
# Requires: python-twitter, requests, requests-oauthlib, sqlite3

# main dependencies
import twitter
import sqlite3
import sys

# constants
SQLDB = 'facts.db'
factsTable = 'facts'
forceBreak = '|'  # used to force a break in the tweet
attempts = 0

# internal dependencies
import credentials
from systemlog import logger


def getRandomMessage():
	""" Chooses a random message, prioritizing messages that have been posted the least in the past. """
	try:
		with sqlite3.connect(SQLDB) as database:
			(rowID, addedDate, category, message, source, media, usedCount) = database.cursor().execute('SELECT * FROM {} ORDER BY usedCount, RANDOM() DESC limit 1'.format(factsTable)).fetchone()
			logger.info('===============')
			logger.info('1/4 - Retrieval successful')
			logger.info('1/4 - Message: {}'.format(message))
			logger.info('1/4 - Media: {}'.format(media))
			logger.info('===============')
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

	global attempts

	if 'notweet' in sys.argv:
		logger.info('3/4 - Skipping Tweet.')
		return True

	try:
		messages = message.split(forceBreak)
		images = media.split(forceBreak)

		# Make sure both lists have the same amount of items and zip
		diff = len(messages) - len(images)
		images = images + [None for x in range(diff)]
		firstTweet = True

		for (message, image) in zip(messages, images):
			if firstTweet:
				response = api.PostUpdate(status=message, media=image)
			else:  # not the first tweet
				response = api.PostUpdate(status=message, media=image, in_reply_to_status_id=response.id)
			logger.info('3/4 - Tweet ID {} sent successfully: {}'.format(str(response.id), message))
			firstTweet = False
		logger.info('===============')

	except Exception as e:
		attempts += 1
		if attempts < 3:
			logger.info('3/4 - Attempt {} failed. Error message was: {}. Trying again. \n==============='.format(str(attempts), str(e.message)))
			main()
		else:
			logger.critical('3/4 - Attempt {} failed. Error message was: {}. \n==============='.format(str(attempts), str(e.message)))
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
	return True


def main():
	global api, message
	(rowID, message, media, usedCount) = getRandomMessage()
	if message:
		api = connnectToTwitter()
		if api:
			result = tweet(message, api, media)
			if result:
				result = markUsed(rowID, usedCount + 1)
				if result:
					logger.critical('Post Successful!\nMessage: {}\nMedia: {}'.format(message, media))
	return


main()
