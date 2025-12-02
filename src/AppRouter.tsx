import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Landing } from './Landing';
import { Plans } from './Plans';
import { Help } from './Help';
import { Checkout } from './Checkout';
import { Success } from './Success';
import { Profile } from './Profile';
import App from './App';
import { Login } from './Login';
import Overlay from './Overlay';

export const AppRouter: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/plans" element={<Plans />} />
      <Route path="/help" element={<Help />} />
      <Route path="/login" element={<Login />} />
      <Route path="/checkout" element={<Checkout />} />
      <Route path="/success" element={<Success />} />
      <Route path="/profile" element={<Profile />} />
      <Route path="/app" element={<App />} />
      <Route path="/overlay" element={<Overlay />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

