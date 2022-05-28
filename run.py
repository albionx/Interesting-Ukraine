#!/usr/bin/env python
# Requires: python-twitter, requests, requests-oauthlib, sqlite3

# main dependencies
import twitter
import sqlite3
import sys
import argparse

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
			if vars(args)['rowid']:
				(rowID, addedDate, category, message, source, media, usedCount) = database.cursor().execute('SELECT * FROM {} WHERE rowID = {}'.format(factsTable, vars(args)['rowid'])).fetchone()
			else:
				(rowID, addedDate, category, message, source, media, usedCount) = database.cursor().execute('SELECT * FROM {} ORDER BY usedCount, RANDOM() DESC limit 1'.format(factsTable)).fetchone()
			logger.info('===============')
			logger.info('1/4 - Retrieval successful: {}'.format(message[:40] + '...'))
			logger.info('===============')
	except:
		logger.critical('===============\n1/4 - Retrieval failed. Unable to retrieve a message from the DB. Notifying over email.\n===============')
		return None
	return (rowID, message, media, usedCount)


def connnectToTwitter():
	""" Connects to Twitter. Uses the Credentials file to isolate credentials from the main running script. """

	if vars(args)['badcredentials']:
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

	if vars(args)['notweet']:
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
			logger.critical('3/4 - Attempt {} failed. Message: {}. Image: {}. Error message was: {}. \n==============='.format(str(attempts), message, image, str(e.message)))
		return None
	return True


def markUsed(rowID, usedCount):
	""" Marks messages as used, helping prevent message duplication when posting. """

	if vars(args)['notweet']:
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

	global api, message, args

	# Enable argument parsing
	parser = argparse.ArgumentParser(description='Run the Twitter bot. More more details, visit: https://github.com/albionx/Interesting-Ukraine')
	parser.add_argument('--notweet', action='store_true', help='Skip tweeting and making the message as used.')
	parser.add_argument('--badcredentials', action='store_true', help='Uses intentionally wrong credentials to trigger an error.')
	parser.add_argument('--rowid', type=int, default=None, help='Integer. Uses the specific RowID instead of selecting one as usual.')
	args = parser.parse_args()

	# Get started
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
