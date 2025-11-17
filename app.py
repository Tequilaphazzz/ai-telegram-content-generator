import os
import asyncio
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
import content_generator as cg

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Ensure the static directories exist
os.makedirs("static/generated", exist_ok=True)
os.makedirs("static/fonts", exist_ok=True)


# TODO: Don't forget to place a font file (e.g., Arial.ttf) in the static/fonts folder

@app.route('/', methods=['GET', 'POST'])
def index():
    # Use sessions to store state between requests
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
                    error = "Topic cannot be empty!"
                else:
                    # Reset the old job and start a new one
                    job = {'topic': topic, 'status': 'text_generation'}
                    job['post_text'] = cg.generate_post_text(topic)
                    if not job['post_text']:
                        error = "Failed to generate text. Please try again."
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
                    error = "Failed to generate image prompt."
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
                    error = "Failed to generate headline or process image."
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
                session['job'] = job  # Save before the asynchronous operation

                # Run the asynchronous publishing function
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
            error = f"An unexpected error occurred: {e}"
            job['status'] = 'error'

        session['job'] = job
        if error:
            session['job']['error'] = error

        return redirect(url_for('index'))

    return render_template('index.html', job=session.get('job'))


if __name__ == '__main__':
    app.run(debug=True)
