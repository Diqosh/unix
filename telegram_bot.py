import asyncio
import os
from aiogram import Bot, Dispatcher, types
from PIL import Image
import pytesseract
from openai import AsyncOpenAI
from dotenv import load_dotenv
from openai.types.chat import ChatCompletion

load_dotenv()

prompt = "I will provide you test please answer right as possible write only answer the text can be broken so u can fill in"

# Bot initialization
TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher()

client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))


@dp.message(lambda message: message.photo)
async def handle_photo(message: types.Message):
    try:
        print("Received photo message")  # Debug log

        # Get the last (highest resolution) photo from the list
        file = await bot.get_file(message.photo[-1].file_id)
        print("Got file")  # Debug log

        download_file = await bot.download_file(file.file_path)
        print("Downloaded file")  # Debug log

        photo = Image.open(download_file)
        print("Opened image")  # Debug log

        # Perform OCR
        text = pytesseract.image_to_string(photo, lang="eng")
        print(f"OCR Result: {text}")  # Debug log

        if text.strip():
            print("Starting OpenAI request")  # Debug log
            completion: ChatCompletion = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    # {"role": "system", "content": f"Also learn this for answering question {knowledge}"},
                    {"role": "user", "content": text}
                ],
            )
            print("Got OpenAI response")  # Debug log
            response_text = completion.choices[0].message.content
            print(f"Response text: {response_text}")  # Debug log

            await message.answer(response_text)  # Changed from reply to answer
        else:
            await message.answer("No text was detected in this image.")

    except Exception as e:
        print(f"Error occurred: {str(e)}")  # Debug log
        await message.answer(f"Sorry, there was an error processing your image. Error: {str(e)}")


@dp.message()
async def handle_other_messages(message: types.Message):
    await message.answer("Please send a photo containing text to extract.")


async def main():
    try:
        print("Bot starting...")
        # print(knowledge)
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user.")