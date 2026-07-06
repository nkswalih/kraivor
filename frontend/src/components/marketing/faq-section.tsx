'use client';

import { useState } from 'react';
import { CaretDown } from '@phosphor-icons/react';

const FAQS = [
  { question: "What is Kraivor's Production Readiness Score?", answer: "It's an AI-driven evaluation of your codebase's scalability, security, and maintainability. It predicts potential failures before they happen in production." },
  { question: 'Can I switch plans later?', answer: 'Yes, you can upgrade or downgrade your plan at any time. Your billing is prorated accordingly.' },
  { question: "What is included in the Team plan's AI Assistant?", answer: 'The Team plan includes 1000 AI query credits per month, allowing your team to ask extensive questions about your codebase.' },
  { question: 'Do you offer custom enterprise solutions?', answer: 'Contact our sales team for custom integrations, dedicated support, and tailored solutions for your organization.' },
  { question: 'How does the async processing work?', answer: 'Any operation over 500ms is handled in the background. Results are pushed via WebSocket or polled, ensuring immediate HTTP responses and 10,000+ concurrent users.' },
  { question: 'What is the refund policy?', answer: 'We offer a 14-day money-back guarantee on all plans. If you are not satisfied, request a full refund within 14 days of purchase.' },
];

export function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="divide-y divide-[var(--krait-border)]">
      {FAQS.map((faq, i) => {
        const isOpen = openIndex === i;
        return (
          <div key={i}>
            <button
              onClick={() => setOpenIndex(isOpen ? null : i)}
              className="flex w-full items-center justify-between py-4 text-left transition-colors"
            >
              <h4 className="text-sm font-medium text-[var(--text-primary)] pr-4">{faq.question}</h4>
              <CaretDown
                size={14}
                weight="bold"
                className={`shrink-0 text-[var(--text-tertiary)] transition-transform ${
                  isOpen ? 'rotate-180' : ''
                }`}
              />
            </button>
            <div className={`overflow-hidden transition-all ${isOpen ? 'max-h-40 pb-4' : 'max-h-0'}`}>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{faq.answer}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
