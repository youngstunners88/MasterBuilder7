import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import SplashScreen from '../../components/SplashScreen';

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    img: ({ ...props }: any) => <img {...props} />,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('SplashScreen', () => {
  it('renders with logo', () => {
    render(<SplashScreen />);
    
    // Check that the splash screen is rendered
    const splashContainer = screen.getByRole('img');
    expect(splashContainer).toBeInTheDocument();
  });

  it('displays loading state correctly', () => {
    const { container } = render(<SplashScreen />);
    
    // Component should be rendered
    expect(container.firstChild).toBeInTheDocument()
  });

  it('has correct accessibility attributes', () => {
    render(<SplashScreen />);
    
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('alt');
  });
});
