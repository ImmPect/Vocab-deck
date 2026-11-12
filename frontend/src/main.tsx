/** Точка входа: store (Flux), маршрутизатор, глобальные стили и токены. */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import { RouterProvider } from 'react-router-dom';
import { router } from './app/router';
import { connectBrowserEvents, store } from './app/store';
import './app/styles/global.css';

connectBrowserEvents(store);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={store}>
      <RouterProvider router={router} />
    </Provider>
  </StrictMode>,
);
