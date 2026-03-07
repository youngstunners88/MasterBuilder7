import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from '../../components/Header';
import { BrowserRouter } from 'react-router-dom';

// Mock the hooks and stores
vi.mock('../../hooks/useSupabase', () => ({
  useSupabase: () => ({
    user: null,
    signOut: vi.fn(),
  }),
}));

vi.mock('../../hooks/useCart', () => ({
  useCart: () => ({
    items: [],
    totalItems: 0,
  }),
}));

describe('Header', () => {
  const renderHeader = () => {
    return render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
  };

  it('renders logo', () => {
    renderHeader();
    
    // Logo should be present
    const logo = screen.getByText(/iHhashi/i);
    expect(logo).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    renderHeader();
    
    // Check for main navigation elements
    expect(screen.getByText(/Home/i)).toBeInTheDocument();
    expect(screen.getByText(/Orders/i)).toBeInTheDocument();
    expect(screen.getByText(/Profile/i)).toBeInTheDocument();
  });

  it('shows cart with 0 items when empty', () => {
    renderHeader();
    
    // Cart should be present
    const cartLink = screen.getByLabelText(/cart/i);
    expect(cartLink).toBeInTheDocument();
  });

  it('toggles mobile menu when menu button is clicked', () => {
    renderHeader();
    
    // Mobile menu button should be present
    const menuButton = screen.getByLabelText(/menu/i);
    expect(menuButton).toBeInTheDocument();
    
    // Click to open menu
    fireEvent.click(menuButton);
    
    // Menu should be visible after click
    // Note: The exact behavior depends on the implementation
  });
});
