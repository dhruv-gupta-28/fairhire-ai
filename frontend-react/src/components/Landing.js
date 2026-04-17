import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Shield, BarChart3, FileText, Target } from "lucide-react";

const Landing = () => {

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative min-h-[85vh] flex items-center justify-center px-4 overflow-hidden bg-[#000000]">
        <div className="hero-content relative z-10 text-center max-w-3xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 leading-tight">
            AI-Powered Fair Hiring
          </h1>
          <p className="text-base text-gray-400 mb-6 max-w-xl mx-auto leading-relaxed">
            Detect bias in your hiring data, analyze resumes with AI, and match
            candidates to jobs ethically.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to="/register"
              className="btn-primary text-sm px-6 py-3 flex items-center justify-center group"
            >
              Get Started Free
              <ArrowRight className="ml-2 w-4 h-4" />
            </Link>
            <Link to="/login" className="btn-secondary text-sm px-6 py-3">
              Sign In
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-white mb-2">
              Comprehensive Hiring Suite
            </h2>
            <p className="text-sm text-gray-400 max-w-xl mx-auto">
              Everything you need to hire fairly and effectively
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="feature-card card p-8 text-center text-gray-300">
              <div className="w-16 h-16 bg-[#111111] border border-[#333333] rounded-md flex items-center justify-center mx-auto mb-6">
                <BarChart3 className="w-8 h-8 text-blue-500" />
              </div>
              <h3 className="text-2xl font-semibold text-white mb-4">
                Bias Detection
              </h3>
              <p className="text-gray-400">
                Analyze your hiring data for gender, age, race, and other biases
                using simple ML algorithms.
              </p>
            </div>

            <div className="feature-card card p-8 text-center text-gray-300">
              <div className="w-16 h-16 bg-[#111111] border border-[#333333] rounded-md flex items-center justify-center mx-auto mb-6">
                <FileText className="w-8 h-8 text-green-500" />
              </div>
              <h3 className="text-2xl font-semibold text-white mb-4">
                Resume Analysis
              </h3>
              <p className="text-gray-400">
                Extract key information from PDF and DOCX resumes instantly.
              </p>
            </div>

            <div className="feature-card card p-8 text-center text-gray-300">
              <div className="w-16 h-16 bg-[#111111] border border-[#333333] rounded-md flex items-center justify-center mx-auto mb-6">
                <Target className="w-8 h-8 text-purple-500" />
              </div>
              <h3 className="text-2xl font-semibold text-white mb-4">
                Job Matching
              </h3>
              <p className="text-gray-400">
                Match candidates to job descriptions directly through resume file analysis.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-4 bg-gray-900/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">How It Works</h2>
            <p className="text-xl text-gray-400">
              Simple, powerful, ethical hiring in three steps
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center mx-auto mb-6 text-white font-bold text-xl">
                1
              </div>
              <h3 className="text-2xl font-semibold text-white mb-4">
                Upload & Analyze
              </h3>
              <p className="text-gray-400 text-sm">
                Upload your hiring data or candidate resumes. Our AI extracts key information.
              </p>
            </div>

            <div className="text-center">
              <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center mx-auto mb-6 text-white font-bold text-xl">
                2
              </div>
              <h3 className="text-2xl font-semibold text-white mb-4">
                Get Insights
              </h3>
              <p className="text-gray-400 text-sm">
                Receive detailed fairness scores, and match candidates easily.
              </p>
            </div>

            <div className="text-center">
              <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center mx-auto mb-6 text-white font-bold text-xl">
                3
              </div>
              <h3 className="text-2xl font-semibold text-white mb-4">
                Make Better Decisions
              </h3>
              <p className="text-gray-400 text-sm">
                Use practical tools to review metrics accurately.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to Transform Your Hiring?
          </h2>
          <p className="text-xl text-gray-400 mb-8">
            Join thousands of companies using FairHire AI to build fairer,
            better teams.
          </p>
          <Link
            to="/register"
            className="btn-primary text-xl px-10 py-5 flex items-center justify-center mx-auto max-w-xs group"
          >
            Start Free Trial
            <ArrowRight className="ml-2 w-6 h-6" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 border-t border-gray-800">
        <div className="max-w-6xl mx-auto text-center">
          <div className="flex items-center justify-center mb-6">
            <Shield className="w-8 h-8 text-blue-400 mr-3" />
            <span className="text-2xl font-bold text-white">FairHire AI</span>
          </div>
          <p className="text-gray-400 mb-6">
            Building the future of ethical AI hiring
          </p>
          <div className="flex justify-center space-x-6 text-sm text-gray-500">
            <button className="hover:text-gray-300">Privacy</button>
            <button className="hover:text-gray-300">Terms</button>
            <button className="hover:text-gray-300">Support</button>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
