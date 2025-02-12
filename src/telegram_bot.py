## Copyright 2019
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##    http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

import argparse
from caption import get_question
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
from functools import partial
import logging
import random
from evaluate_chatbot import load_chatbot_model, give_feedback
import string
import os

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger()
logger.setLevel(logging.INFO)
idx = 0
img_path = ''
shown_img_paths = []


def main(opts):

    global encoder, decoder, searcher, voc, img_directory, TOKEN, test_data_file

    TOKEN = opts.token
    img_directory = opts.img_dir
    test_data_file = opts.filenames

    # Load chatbot model
    checkpoint_iter = 13000
    load_model = os.path.join('checkpoints_dialog_model/cornell_model/cornell-movie-dialogs/fine_tunned_cornell', '{}_checkpoint.tar'.format(checkpoint_iter))
    encoder, decoder, searcher, voc = load_chatbot_model(load_model)

    # Create Updater object and attach dispatcher to it
    updater = Updater(TOKEN)
    # link our Updater object with dispatcher
    dispatcher = updater.dispatcher
    print("Bot started")

    # Add command handler to dispatcher and start therapy
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    # If no, send another image
    dispatcher.add_handler(CommandHandler('CHANGE', send_img))

    # generate question
    dispatcher.add_handler(CommandHandler('YES', partial(ask_first_question, img=img_path)))

    dispatcher.add_handler(CommandHandler('EXIT', exit))

    dispatcher.add_handler(CommandHandler('pass', pass_q))

    # dispatcher.add_error_handler(callback)

    #  handle all the non-command messages
    dispatcher.add_handler(MessageHandler(Filters.text, feedback_and_question))

    # Start the bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


def callback(update, context, error):
    update.message.reply_text('The session has finished. It has been a pleasure talking to you! See you soon :) ')


def start(update, context):
    global img_path
    img_path = get_random_pic()
    print(img_path)
    update.message.reply_text("Hello! Let's start the reminiscence therapy!")
    context.bot.sendPhoto(chat_id=update.message.chat_id, photo=open(img_path, 'rb'),
                  caption="Do you want to talk about this image? Tap /YES or /CHANGE")


def exit(update, context):
    update.message.reply_text('The session has finished. It has been a pleasure talking to you! See you soon :) ')


def pass_q(update, context):
    next_question(update, context)


def say_hello():
    msg = ['Hello!', 'Hello! How are you doing?', 'Hi', 'What\'s up?']
    return random.choice(msg)


def send_img(update, context):
    global img_path

    img_path = get_random_pic()

    if img_path == '':
        exit(update, context)
    else:
        # chat_id = bot.get_updates()[-1].message.chat_id
        context.bot.sendPhoto(chat_id=update.message.chat_id, photo=open(img_path, 'rb'),
                      caption="What about this one? Tap /YES or /CHANGE")


def ask_first_question(update, context, img):
    global img_path, questions, idx

    print("Image selected, generating questions...")

    update.message.reply_text("Great! Try to think in that moment as it was now")
    # update.message.reply_text("I'll think some questions...")
    update.message.reply_text("Explain me this image, answering my questions...")

    # Generate questions
    questions = get_question(img_path)
    idx = 0

    # Ask first predetermined question about time
    time_q = time_question()
    update.message.reply_text(time_q)
    print(time_q)


def time_question():
    q = ['When was this picture taken?', 'How long ago was this picture taken?', 'What year was this photo taken?', 'How old were you when this picture was taken?']
    return random.choice(q)


def feedback_and_question(update, context):

    # Feedback
    print(update.message.text)
    out = give_feedback(encoder, decoder, searcher, voc, update.message.text)
    out = "".join([" " + i if not i.startswith("'") and i not in string.punctuation else i for i in out]).strip()

    out = out.split('.', 1)[0]
    if '?' in out:
        out = out.split('?', 1)[0] + '?'

    if out == 'what?':
       out = 'Nice'

    if out == 'no':
       out = 'ok'

    update.message.reply_text(out)

    next_question(update, context)


def next_question(update, context):
    global questions, idx

    try:
        # Show questions in shell
        # for q in questions:
        #     print(q)

        num_q = len(questions)

        if idx == 0 and idx < num_q:
            update.message.reply_text(questions[0] + ' /pass')
        if idx == 1 and idx < num_q:
            update.message.reply_text(questions[1] + ' /pass')
        if idx == 2 and idx < num_q:
            update.message.reply_text(questions[2] + ' /pass')
        if idx == 3 and idx < num_q:
            update.message.reply_text(questions[3] + ' /pass')
        if idx == 4 and idx < num_q:
            update.message.reply_text(questions[4] + ' /pass')
        idx += 1

        if idx > num_q:
            update.message.reply_text('Let\'s continue with another image, tap /CHANGE ! if you want to leave tap /EXIT')
            idx = 0

    except Exception as e:
        print(e)


def get_random_pic():

    count = 0

    global shown_img_paths

    with open(test_data_file) as f:
        lines = f.readlines()

    img_path = random.choice(lines)

    while img_path in shown_img_paths:
        img_path = random.choice(lines)
        count += 1
        if count == 30:
            return ''

    if img_path not in shown_img_paths:
        shown_img_paths.append(img_path)

    print('image path ', img_path)

    return img_directory + img_path.rstrip()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--token', type=str, help='Bot token', default='110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw')
    parser.add_argument('--filenames', type=str, help='text  file with filenames of images',
                        default='data/filenames_list/my_test_filenames.txt')
    parser.add_argument('--img_dir', type=str, help='Directory of images', default='data/my_test_images/')

    opts = parser.parse_args()

    main(opts)
