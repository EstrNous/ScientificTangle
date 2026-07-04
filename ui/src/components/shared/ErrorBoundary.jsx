import { Component } from 'react';
import i18n from '../../i18n/index.js';
import { useMock } from '../../utils/runtimeMode.js';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary]', error, errorInfo?.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full min-h-[12rem] flex-col items-center justify-center gap-4 p-6 text-center">
          <p className="text-base font-medium text-gray-900 dark:text-slate-100">
            {i18n.t('errors.boundaryTitle')}
          </p>
          <p className="max-w-md text-sm text-nn-gray dark:text-slate-400">
            {i18n.t('errors.boundaryMessage')}
          </p>
          {useMock && import.meta.env.DEV && (
            <p className="max-w-md text-xs text-nn-gray dark:text-slate-500">
              {i18n.t('errors.boundaryMockHint')}
            </p>
          )}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <button
              type="button"
              onClick={this.handleRetry}
              className="rounded-lg border border-nn-border px-3 py-1.5 text-sm text-gray-900 hover:bg-nn-gray-light dark:border-slate-600 dark:text-slate-100 dark:hover:bg-slate-800"
            >
              {i18n.t('errors.retry')}
            </button>
            <button
              type="button"
              onClick={this.handleReload}
              className="rounded-lg bg-nn-blue px-3 py-1.5 text-sm text-white hover:bg-nn-blue/90"
            >
              {i18n.t('errors.reload')}
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
