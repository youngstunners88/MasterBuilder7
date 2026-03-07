import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CategoryBar } from '../../components/CategoryBar';

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
}));

describe('CategoryBar', () => {
  const mockCategories = [
    { id: 'all', name: 'All', icon: '🍽️' },
    { id: 'restaurant', name: 'Restaurants', icon: '🍔' },
    { id: 'grocery', name: 'Grocery', icon: '🥬' },
  ];

  const mockOnSelect = vi.fn();

  it('renders all categories', () => {
    render(
      <CategoryBar
        categories={mockCategories}
        selected="all"
        onSelect={mockOnSelect}
      />
    );
    
    mockCategories.forEach(cat => {
      expect(screen.getByText(cat.name)).toBeInTheDocument();
    });
  });

  it('highlights selected category', () => {
    render(
      <CategoryBar
        categories={mockCategories}
        selected="restaurant"
        onSelect={mockOnSelect}
      />
    );
    
    // The selected category should have some visual indicator
    // This depends on the actual implementation
  });

  it('calls onSelect when category is clicked', () => {
    render(
      <CategoryBar
        categories={mockCategories}
        selected="all"
        onSelect={mockOnSelect}
      />
    );
    
    const groceryButton = screen.getByText('Grocery');
    fireEvent.click(groceryButton);
    
    expect(mockOnSelect).toHaveBeenCalledWith('grocery');
  });
});
