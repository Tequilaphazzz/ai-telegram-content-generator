import os
import asyncio
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
import content_generator as cg

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Убедимся, что папки для статики существуют
os.makedirs("static/generated", exist_ok=True)
os.makedirs("static/fonts", exist_ok=True)


# TODO: Не забудьте положить файл шрифта (например, Arial.ttf) в папку static/fonts

@app.route('/', methods=['GET', 'POST'])
def index():
    # Используем сессии для хранения состояния между запросами
    if 'job' not in session:
        session['job'] = {}

    if request.method == 'POST':
        action = request.form.get('action')
        job = session['job']
        error = None

        try:
            if action == 'start_generation':
                topic = request.form.get('topic')
                if not topic:
                    error = "Тема не может быть пустой!"
                else:
                    # Сбрасываем старую работу и начинаем новую
                    job = {'topic': topic, 'status': 'text_generation'}
                    job['post_text'] = cg.generate_post_text(topic)
                    if not job['post_text']:
                        error = "Не удалось сгенерировать текст. Попробуйте снова."
                        job['status'] = 'error'

            elif action == 'regenerate_text':
                job['status'] = 'text_generation'
                job['post_text'] = cg.generate_post_text(job['topic'])

            elif action == 'approve_text':
                job['status'] = 'image_generation'
                prompt = cg.generate_image_prompt(job['post_text'])
                if prompt:
                    image_path = os.path.join("static", "generated", "post_image.png")
                    job['post_image'] = cg.generate_image(prompt, image_path)
                else:
                    error = "Не удалось сгенерировать промт для изображения."
                    job['status'] = 'error'

            elif action == 'regenerate_image':
                job['status'] = 'image_generation'
                prompt = cg.generate_image_prompt(job['post_text'])
                image_path = os.path.join("static", "generated", "post_image.png")
                job['post_image'] = cg.generate_image(prompt, image_path)

            elif action == 'approve_image':
                job['status'] = 'headline_generation'
                job['story_headline'] = cg.generate_story_headline(job['post_text'])
                if job.get('post_image') and job.get('story_headline'):
                    story_image_path = os.path.join("static", "generated", "story_image.png")
                    job['story_image'] = cg.create_story_image(job['post_image'], job['story_headline'],
                                                               story_image_path)
                else:
                    error = "Не удалось сгенерировать заголовок или обработать изображение."
                    job['status'] = 'error'

            elif action == 'regenerate_headline':
                job['status'] = 'headline_generation'
                job['story_headline'] = cg.generate_story_headline(job['post_text'])
                story_image_path = os.path.join("static", "generated", "story_image.png")
                job['story_image'] = cg.create_story_image(job['post_image'], job['story_headline'], story_image_path)

            elif action == 'approve_all':
                job['status'] = 'approved'

            elif action == 'publish':
                job['status'] = 'publishing'
                session['job'] = job  # Сохраняем перед асинхронной операцией

                # Запускаем асинхронную функцию публикации
                result = asyncio.run(cg.publish_to_telegram(
                    job['post_text'],
                    job['post_image'],
                    job['story_image']
                ))
                job['publish_result'] = result
                job['status'] = 'finished'

            elif action == 'reset':
                session.pop('job', None)
                return redirect(url_for('index'))

        except Exception as e:
            error = f"Произошла непредвиденная ошибка: {e}"
            job['status'] = 'error'

        session['job'] = job
        if error:
            session['job']['error'] = error

        return redirect(url_for('index'))

    return render_template('index.html', job=session.get('job'))


if __name__ == '__main__':
    app.run(debug=True)