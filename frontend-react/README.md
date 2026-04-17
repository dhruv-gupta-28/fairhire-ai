# FairHire AI - React Frontend

A modern React frontend for the FairHire AI SaaS platform, providing an intuitive interface for bias detection, resume analysis, job matching, and analysis history.

## Features

- **Modern UI**: Built with React and Tailwind CSS for a sleek, professional interface
- **Authentication**: JWT-based login and registration system
- **Bias Detection**: Upload and analyze CSV datasets for hiring bias
- **Resume Analysis**: Extract information from PDF resumes using AI
- **Job Matching**: Match candidates with job requirements
- **Analysis History**: View past analyses and download reports
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Tech Stack

- **React 18**: Modern React with hooks and functional components
- **React Router**: Client-side routing for navigation
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API communication
- **React Dropzone**: File upload functionality
- **Lucide React**: Beautiful icons

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Running FairHire AI backend server

### Installation

1. Navigate to the frontend directory:

   ```bash
   cd frontend-react
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start the development server:

   ```bash
   npm start
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
src/
├── components/          # React components
│   ├── Navbar.js       # Navigation bar
│   ├── Login.js        # Login form
│   ├── Register.js     # Registration form
│   ├── Dashboard.js    # Main dashboard
│   ├── Analysis.js     # Bias analysis interface
│   ├── ResumeAnalysis.js # Resume analysis interface
│   ├── JobMatching.js  # Job matching interface
│   └── History.js      # Analysis history
├── contexts/           # React contexts
│   └── AuthContext.js  # Authentication context
├── App.js             # Main app component
├── App.css            # Custom styles
└── index.js           # App entry point
```

## API Integration

The frontend communicates with the Flask backend API running on `http://localhost:5000`. Key endpoints:

- `POST /auth/login` - User authentication
- `POST /auth/register` - User registration
- `POST /analyze` - Bias analysis
- `POST /resume/analyze` - Resume analysis
- `POST /job/match` - Job matching
- `GET /history/analyses` - Analysis history
- `GET /history/reports` - Report history

## Features Overview

### Authentication

- Secure JWT-based authentication
- Role-based access control (user/recruiter/admin)
- Persistent login sessions

### Dashboard

- Overview of analysis statistics
- Quick access to all features
- Recent activity feed

### Bias Analysis

- CSV file upload with drag-and-drop
- Real-time analysis progress
- Detailed fairness metrics and recommendations
- Visual score representation

### Resume Analysis

- PDF resume upload
- AI-powered information extraction
- Skills detection and scoring
- Improvement recommendations

### Job Matching

- Text-based resume and job description input
- Similarity scoring algorithms
- Skills matching analysis
- Personalized recommendations

### History Management

- Complete analysis history
- Report download functionality
- Chronological organization
- Status tracking

## Development

### Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

### Code Style

- Uses ESLint for code linting
- Follows React best practices
- Consistent component structure
- Proper error handling

## Deployment

1. Build the production version:

   ```bash
   npm run build
   ```

2. Serve the `build` folder with any static server

3. Configure the API base URL for production environment

## Contributing

1. Follow the existing code style and structure
2. Add proper error handling
3. Test components thoroughly
4. Update documentation as needed

## License

This project is part of the FairHire AI platform.
