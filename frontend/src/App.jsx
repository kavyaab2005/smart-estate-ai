import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import BuyerDashboard from './pages/BuyerDashboard';
import AgentDashboard from './pages/AgentDashboard';
import AdminDashboard from './pages/AdminDashboard';
import PropertySearch from './pages/PropertySearch';
import PropertyDetail from './pages/PropertyDetail';
import MapView from './pages/MapView';
import Compare from './pages/Compare';
import Favorites from './pages/Favorites';
import ChatAssistant from './pages/ChatAssistant';
import DocumentVerification from './pages/DocumentVerification';
import AddProperty from './pages/AddProperty';
import EditProperty from './pages/EditProperty';
import AdminProperties from './pages/AdminProperties';

function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/search" element={<PropertySearch />} />
        <Route path="/property/:id" element={<PropertyDetail />} />
        <Route path="/map" element={<MapView />} />
        <Route path="/compare" element={<Compare />} />
        <Route path="/favorites" element={<Favorites />} />
        <Route path="/chat" element={<ChatAssistant />} />
        <Route path="/verify-documents" element={<DocumentVerification />} />
        <Route
          path="/buyer"
          element={
            <ProtectedRoute allowedRoles={['buyer']}>
              <BuyerDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/agent"
          element={
            <ProtectedRoute allowedRoles={['agent']}>
              <AgentDashboard />
            </ProtectedRoute>
          }
        />
        <Route
  path="/agent/edit-property/:propertyId"
  element={
    <ProtectedRoute allowedRoles={['agent']}>
      <EditProperty />
    </ProtectedRoute>
  }
/>

        <Route
  path="/agent/add-property"
  element={
    <ProtectedRoute allowedRoles={['agent']}>
      <AddProperty />
    </ProtectedRoute>
  }
/>
        <Route
          path="/admin"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
  path="/admin/properties"
  element={
    <ProtectedRoute allowedRoles={['admin']}>
      <AdminProperties />
    </ProtectedRoute>
  }
/>
      </Routes>
    </BrowserRouter>
  );
}

export default App;