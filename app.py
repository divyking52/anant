from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph
from newspaper import Article
import spacy
import regex  # Use 'regex' instead of 're'

app = Flask(_name_)

# Load the spaCy model with 'sentencizer'
nlp = spacy.load("en_core_web_lg", exclude=['parser', 'ner'])
sentencizer = nlp.add_pipe("sentencizer")

def scrape_text_from_url(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"Error extracting text from URL: {str(e)}")
        return f"Error extracting text from URL: {str(e)}"

def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PdfReader(pdf_file)
        text = ''
        for page_num in range(len(pdf_reader.pages)):
            text += pdf_reader.pages[page_num].extract_text()
        return text
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

def preprocess_text(text):
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    return sentences

def extractive_summarization(sentences, num_sentences=3):
    sentence_scores = [(i, sum(token.is_alpha for token in nlp(sentence))) for i, sentence in enumerate(sentences)]
    summary_sentences = sorted(sentence_scores, key=lambda x: x[1], reverse=True)[:num_sentences]
    summary = ' '.join(sentences[i] for i, _ in summary_sentences)
    return summary

def create_pdf(summary):
    pdf_filename = 'summarized_text.pdf'

    # Create a PDF document
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    styles = getSampleStyleSheet()

    # Create a list of paragraphs with proper formatting
    paragraphs = [Paragraph("Summarized Text:", styles['Heading1'])]

    # Split the summary into paragraphs for better formatting
    summary_paragraphs = summary.split('\n')
    paragraphs += [Paragraph(paragraph, styles['BodyText'], encoding='utf-8') for paragraph in summary_paragraphs]

    # Build the PDF document
    doc.build(paragraphs)

    return pdf_filename

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        choice = request.form.get('choice')
        title = ''
        text = ''

        if choice == 'url':
            url = request.form.get('url')
            text = scrape_text_from_url(url)
            if not text.startswith("Error"):
                title = "Title"  # You might want to get the title separately if needed
            else:
                return render_template('index.html', error=text)
        elif choice == 'pdf':
            pdf_file = request.files['pdf_file']
            text = extract_text_from_pdf(pdf_file)
        elif choice == 'text':
            text = request.form.get('user_text')

        sentences = preprocess_text(text)
        summary = extractive_summarization(sentences)
        cleaned_summary = regex.sub(r'\[\d+\]', '', summary)  # Use 'regex' instead of 're'

        # Create a PDF file with the summarized text using ReportLab
        pdf_filename = create_pdf(cleaned_summary)

        original_text_length = len(text)
        summarized_text_length = len(cleaned_summary)

        return render_template('result.html', summary=cleaned_summary,
                               original_text_length=original_text_length, summarized_text_length=summarized_text_length,
                               pdf_filename=pdf_filename)

    return render_template('index.html')

@app.route('/download_pdf/<filename>', methods=['GET'])
def download_pdf(filename):
    return send_file(filename, as_attachment=True)

if _name_ == "_main_":
    app.run(debug=True)
