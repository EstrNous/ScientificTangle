import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-full flex items-center justify-center text-slate-300 p-6">
          <p>Ошибка интерфейса. Обновите страницу или переключитесь на mock-режим.</p>
        </div>
      );
    }
    return this.props.children;
  }
}
