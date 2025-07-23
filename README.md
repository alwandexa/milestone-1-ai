# iScaps Product Knowledge System with Multimodal AI Support

A comprehensive product knowledge management system with advanced multimodal AI capabilities, built using FastAPI, Streamlit, and LangGraph.

## 🚀 Features

### Core Features
- **Document Management**: Upload, process, and manage PDF documents
- **Product Knowledge Querying**: Intelligent search and retrieval of product information
- **Agentic Workflow**: LangGraph-based conversational AI with memory and context
- **Product Group Organization**: Categorize documents by product groups

### 🖼️ Multimodal AI Capabilities
- **Image Analysis**: Analyze images using GPT-4o-mini multimodal capabilities
- **Text Extraction**: Extract text from images using OCR
- **Combined Analysis**: Process text and images together for comprehensive insights
- **Visual Product Recognition**: Identify and analyze product labels, medical images, and documents

## 🏗️ Architecture

The system follows a clean architecture pattern with the following layers:

```
src/
├── controller/          # API endpoints and request handling
├── usecase/            # Business logic and workflows
├── domain/             # Domain models and entities
├── repository/         # Data access layer (Milvus)
├── infrastructure/     # External services (OpenAI, LangGraph)
└── ports/             # Interface definitions
```

## 🛠️ Technology Stack

- **Backend**: FastAPI, Uvicorn
- **Frontend**: Streamlit
- **AI/ML**: OpenAI GPT-4o-mini, LangChain, LangGraph
- **Vector Database**: Milvus
- **Image Processing**: Pillow (PIL)
- **Document Processing**: PyMuPDF, PyPDF2

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd milestone-1-ai
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Set up environment variables**
   ```bash
   cp .example.env .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   MILVUS_HOST=localhost
   MILVUS_PORT=19530
   ```

4. **Start Milvus (if not already running)**
   ```bash
   docker run -d --name milvus_standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone
   ```

## 🚀 Running the Application

### Start the API Server
```bash
python main.py
```
The API will be available at `http://localhost:8000`

### Start the Streamlit App
```bash
streamlit run product_knowledge_app.py
```
The web interface will be available at `http://localhost:8501`

## 📚 API Endpoints

### Document Management
- `POST /documents/upload` - Upload PDF documents
- `GET /documents` - List all documents
- `DELETE /documents/{id}` - Delete a document

### Product Knowledge Queries
- `POST /product-knowledge/query` - Text-only queries
- `POST /product-knowledge/multimodal-query` - **NEW**: Text + image queries

### Chat Interface
- `POST /chat` - Text-only chat
- `POST /chat/multimodal` - **NEW**: Multimodal chat with images

### Image Analysis
- `POST /analyze-image` - **NEW**: Analyze images with custom prompts

### Product Groups
- `GET /product-groups` - List available product groups
- `GET /documents/search/product-group/{group}` - Search by product group

## 🖼️ Multimodal Features

### Image Analysis
The system can analyze images using GPT-4o-mini's multimodal capabilities:

```python
# Analyze an image with a custom prompt
response = requests.post(
    "http://localhost:8000/analyze-image",
    files={"image": image_file},
    data={"prompt": "What does this medical image show?"}
)
```

### Text Extraction from Images
Automatically extract text from images using OCR:

```python
# The system automatically extracts text from uploaded images
# and combines it with your query for better analysis
```

### Multimodal Product Knowledge Queries
Combine text queries with images for comprehensive analysis:

```python
# Query with both text and image
response = requests.post(
    "http://localhost:8000/product-knowledge/multimodal-query",
    files={"image": image_file},
    data={"query": "What are the side effects of this medication?"}
)
```

## 🎯 Use Cases

### Pharmaceutical Industry
- **Product Label Analysis**: Upload medication labels and ask about ingredients, dosage, side effects
- **Medical Image Analysis**: Analyze medical images alongside product documentation
- **Document Comparison**: Compare visual product information with text documentation

### Healthcare
- **Medical Device Analysis**: Analyze device images and documentation together
- **Patient Education**: Combine visual aids with product information
- **Compliance Checking**: Verify product labels against regulatory requirements

### Research & Development
- **Clinical Trial Documentation**: Analyze trial images with product data
- **Competitive Analysis**: Compare product visuals and documentation
- **Quality Assurance**: Verify product packaging and labeling

## 🔧 Testing

Run the multimodal functionality tests:

```bash
python test_multimodal.py
```

This will test:
- Image analysis capabilities
- Multimodal chat functionality
- Product knowledge queries with images
- API health checks

## 📊 LangGraph Workflow

The system uses an enhanced LangGraph workflow with multimodal support:

1. **Process Multimodal Input**: Extract text from images and combine with queries
2. **Search Documents**: Find relevant document chunks
3. **Evaluate Results**: Determine if context contains answers
4. **Generate Answer**: Create responses using text and image analysis
5. **Modify Query**: Refine queries if needed

## 🎨 Streamlit Interface Features

### Multimodal Chat Interface
- **Image Upload**: Drag and drop or select image files
- **Image Preview**: See uploaded images before analysis
- **Combined Analysis**: Text queries with image context
- **Extracted Text Display**: View text extracted from images
- **Multimodal Badges**: Visual indicators for multimodal responses

### Quick Actions
- **Image Analysis**: Analyze images independently
- **Multimodal Queries**: Pre-defined multimodal question templates
- **Product Group Filtering**: Filter responses by product categories

## 🔒 Security & Performance

- **Input Validation**: All image and text inputs are validated
- **Error Handling**: Graceful fallbacks for failed image processing
- **Memory Management**: Efficient handling of large image files
- **API Rate Limiting**: Built-in protection against abuse

## 🚀 Future Enhancements

- **Video Analysis**: Support for video content analysis
- **Batch Processing**: Process multiple images simultaneously
- **Advanced OCR**: Enhanced text extraction capabilities
- **Custom Models**: Integration with domain-specific models
- **Real-time Analysis**: Live image analysis capabilities

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request
