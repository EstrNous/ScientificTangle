import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import HighlightedText from './HighlightedText.jsx';

describe('HighlightedText', () => {
  it('highlights substring by offsets', () => {
    const text = 'Содержание NiSO4 в растворе';
    render(<HighlightedText text={text} highlightStart={11} highlightEnd={16} />);
    expect(screen.getByText('NiSO4')).toBeInTheDocument();
  });

  it('falls back to string highlight', () => {
    render(<HighlightedText text="alpha beta gamma" highlight="beta" />);
    expect(screen.getByText('beta')).toBeInTheDocument();
  });
});
