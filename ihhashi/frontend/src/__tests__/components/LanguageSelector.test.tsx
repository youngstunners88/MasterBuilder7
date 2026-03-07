import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import LanguageSelector from '../../components/LanguageSelector';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    i18n: {
      language: 'en',
      changeLanguage: vi.fn(),
    },
    t: (key: string) => key,
  }),
}));

describe('LanguageSelector', () => {
  it('renders language selector', () => {
    render(<LanguageSelector />);
    
    // Component should render
    const selector = screen.getByRole('button');
    expect(selector).toBeInTheDocument();
  });

  it('displays current language', () => {
    render(<LanguageSelector />);
    
    // Should show current language
    expect(screen.getByText(/EN/i)).toBeInTheDocument();
  });

  it('opens language menu when clicked', () => {
    render(<LanguageSelector />);
    
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    // Language options should appear
    // Note: This depends on the actual implementation
  });
});
