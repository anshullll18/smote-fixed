import { useState, useEffect } from 'react';
import './Dashboard.css';

function Dashboard({ token, onLogout }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [zipFile, setZipFile] = useState(null);
  const [kNeighbour, setKNeighbour] = useState('');
  const [targetRatio, setTargetRatio] = useState('');
  const [randomState, setRandomState] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [outputInfo, setOutputInfo] = useState(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/auth/user', {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setUser(data);
        } else {
          onLogout();
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [token, onLogout]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.zip')) {
        setZipFile(file);
        setError('');
        setFieldErrors(prev => ({ ...prev, zipFile: '' }));
      } else {
        setFieldErrors(prev => ({ ...prev, zipFile: 'Only .zip files are allowed' }));
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.name.endsWith('.zip')) {
        setZipFile(file);
        setError('');
        setFieldErrors(prev => ({ ...prev, zipFile: '' }));
      } else {
        setFieldErrors(prev => ({ ...prev, zipFile: 'Only .zip files are allowed' }));
      }
    }
  };

  const validateField = (name, value) => {
    const errors = {};

    switch (name) {
      case 'zipFile':
        if (!zipFile) {
          errors.zipFile = 'ZIP file is required';
        }
        break;
      
      case 'kNeighbour':
        if (value && value !== '') {
          const num = parseInt(value, 10);
          if (isNaN(num)) {
            errors.kNeighbour = 'Must be a valid integer';
          } else if (num < 2) {
            errors.kNeighbour = 'Must be greater than 1';
          }
        }
        break;
      
      case 'targetRatio':
        if (value && value !== '') {
          const num = parseFloat(value);
          if (isNaN(num)) {
            errors.targetRatio = 'Must be a valid number';
          } else if (num < 0.0 || num > 1.0) {
            errors.targetRatio = 'Must be between 0.0 and 1.0';
          }
        }
        break;
      
      case 'randomState':
        if (value && value !== '') {
          const num = parseInt(value, 10);
          if (isNaN(num)) {
            errors.randomState = 'Must be a valid integer';
          }
        }
        break;
      
      default:
        break;
    }

    return errors;
  };

  const handleInputChange = (name, value) => {
    switch (name) {
      case 'kNeighbour':
        setKNeighbour(value);
        break;
      case 'targetRatio':
        setTargetRatio(value);
        break;
      case 'randomState':
        setRandomState(value);
        break;
      default:
        break;
    }

    const errors = validateField(name, value);
    setFieldErrors(prev => ({ ...prev, ...errors, [name]: errors[name] || '' }));
  };

  const validateAllFields = () => {
    const errors = {};
    
    if (!zipFile) {
      errors.zipFile = 'ZIP file is required';
    }
    
    Object.assign(errors, validateField('kNeighbour', kNeighbour));
    Object.assign(errors, validateField('targetRatio', targetRatio));
    Object.assign(errors, validateField('randomState', randomState));

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setOutputInfo(null);

    if (!validateAllFields()) {
      setError('Please fix all validation errors before submitting');
      return;
    }

    setSubmitting(true);

    const formData = new FormData();
    formData.append('zipFile', zipFile);
    formData.append('k_neighbour', kNeighbour || 'null');
    formData.append('target_ratio', targetRatio || 'null');
    formData.append('random_state', randomState || 'null');

    try {
      const response = await fetch('http://localhost:5000/api/auth/process', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        let message = 'Error processing file';
        try {
          const errJson = await response.json();
          message = errJson.message || message;
        } catch {

        }
        setError(message);
        return;
      }

      const disposition = response.headers.get('Content-Disposition') || response.headers.get('content-disposition');
      let filename = 'result.zip';
      if (disposition) {
        const utf8Match = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(disposition);
        const plainMatch = /filename\s*=\s*\"?([^\";]+)\"?/i.exec(disposition);
        if (utf8Match) {
          filename = decodeURIComponent(utf8Match[1]);
        } else if (plainMatch) {
          filename = plainMatch[1];
        }
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'result.zip';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setSuccess('File processed successfully! Download started.');
      
      setOutputInfo({
        filename: filename,
        size: (blob.size / (1024 * 1024)).toFixed(2) + ' MB',
        kNeighbour: kNeighbour || 'Auto',
        targetRatio: targetRatio || 'Auto',
        randomState: randomState || 'Auto'
      });

      setZipFile(null);
      setKNeighbour('');
      setTargetRatio('');
      setRandomState('');
      setFieldErrors({});
    } catch (err) {
      console.error(err);
      setError('Connection error');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-content">

        <div className="dashboard-header">
          <div className="header-text">
            <h1>Dashboard</h1>
            <p className="header-subtitle">Manage your data processing tasks</p>
          </div>
          <button onClick={onLogout} className="logout-btn">
            Logout
          </button>
        </div>


        {user && (
          <div className="user-info-card">
            <h2 className="card-title">User Information</h2>
            <div className="user-info-grid">
              <div className="info-item info-item-blue">
                <div className="info-icon">U</div>
                <div>
                  <p className="info-label">Username</p>
                  <p className="info-value">{user.username}</p>
                </div>
              </div>
              <div className="info-item info-item-purple">
                <div className="info-icon">@</div>
                <div>
                  <p className="info-label">Email</p>
                  <p className="info-value">{user.email}</p>
                </div>
              </div>
            </div>
          </div>
        )}


        <div className="processing-card">
          <h2 className="card-title">File Processing</h2>


          {error && (
            <div className="message message-error">
              <span className="message-icon">!</span>
              <p>{error}</p>
            </div>
          )}
          
          {success && (
            <div className="message message-success">
              <span className="message-icon">✓</span>
              <p>{success}</p>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-layout">
              {/* Left Section - Input Fields */}
              <div className="left-section">
                <h3 className="section-title">Input Parameters</h3>


                <div>
                  <label style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '0.5rem', 
                    fontSize: '0.875rem', 
                    fontWeight: '500', 
                    color: '#374151',
                    marginBottom: '0.5rem'
                  }}>
                    Upload Dataset
                    <span className="required-badge">Required</span>
                  </label>
                  <div
                    className={`upload-area ${dragActive ? 'upload-area-active' : ''} ${fieldErrors.zipFile ? 'input-error' : ''}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => document.getElementById('fileInput').click()}
                  >
                    <input
                      id="fileInput"
                      type="file"
                      accept=".zip"
                      onChange={handleFileChange}
                      style={{ display: 'none' }}
                    />
                    <div className="upload-content">
                      {zipFile ? (
                        <>
                          <div className="file-icon">FILE</div>
                          <div className="file-info">
                            <p className="file-label">Selected file:</p>
                            <p className="file-name">{zipFile.name}</p>
                            <p className="file-size">
                              {(zipFile.size / (1024 * 1024)).toFixed(2)} MB
                            </p>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="upload-icon">UPLOAD</div>
                          <div className="upload-text">
                            <p className="upload-primary">Drag and drop your .zip file here</p>
                            <p className="upload-secondary">or click to browse</p>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                  {fieldErrors.zipFile && (
                    <p className="field-error">! {fieldErrors.zipFile}</p>
                  )}
                </div>


                <div className="parameters-grid">
                  <div className="param-field">
                    <label>
                      K Neighbour
                      <span className="optional-badge">Optional</span>
                    </label>
                    <input
                      type="number"
                      value={kNeighbour}
                      onChange={(e) => handleInputChange('kNeighbour', e.target.value)}
                      min="2"
                      className={fieldErrors.kNeighbour ? 'input-error' : ''}
                      placeholder="Enter value (e.g., 5)"
                    />
                    {fieldErrors.kNeighbour ? (
                      <p className="field-error">! {fieldErrors.kNeighbour}</p>
                    ) : (
                      <p className="param-hint">Must be greater than 1 (optional)</p>
                    )}
                  </div>

                  <div className="param-field">
                    <label>
                      Target Ratio
                      <span className="optional-badge">Optional</span>
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={targetRatio}
                      onChange={(e) => handleInputChange('targetRatio', e.target.value)}
                      min="0.0"
                      max="1.0"
                      className={fieldErrors.targetRatio ? 'input-error' : ''}
                      placeholder="Leave empty for auto"
                    />
                    {fieldErrors.targetRatio ? (
                      <p className="field-error">! {fieldErrors.targetRatio}</p>
                    ) : (
                      <p className="param-hint">Between 0.0 and 1.0 (optional)</p>
                    )}
                  </div>

                  <div className="param-field">
                    <label>
                      Random State
                      <span className="optional-badge">Optional</span>
                    </label>
                    <input
                      type="number"
                      value={randomState}
                      onChange={(e) => handleInputChange('randomState', e.target.value)}
                      className={fieldErrors.randomState ? 'input-error' : ''}
                      placeholder="Enter value (e.g., 42)"
                    />
                    {fieldErrors.randomState ? (
                      <p className="field-error">! {fieldErrors.randomState}</p>
                    ) : (
                      <p className="param-hint">Any integer value for reproducibility (optional)</p>
                    )}
                  </div>
                </div>


                <button
                  type="submit"
                  disabled={submitting}
                  className={`submit-btn ${submitting ? 'submit-btn-disabled' : ''}`}
                >
                  {submitting ? (
                    <>
                      <span className="spinner-small"></span>
                      Processing...
                    </>
                  ) : (
                    <>
                      Process File
                    </>
                  )}
                </button>
              </div>

              {/* Right Section - Output Display */}
              <div className="right-section">
                <h3 className="section-title">Output Information</h3>
                
                <div className="output-section">
                  {outputInfo ? (
                    <div className="output-info">
                      <div className="output-item">
                        <span className="output-label">Output File:</span>
                        <span className="output-value">{outputInfo.filename}</span>
                      </div>
                      <div className="output-item">
                        <span className="output-label">File Size:</span>
                        <span className="output-value">{outputInfo.size}</span>
                      </div>
                      <div className="output-item">
                        <span className="output-label">K Neighbour Used:</span>
                        <span className="output-value">{outputInfo.kNeighbour}</span>
                      </div>
                      <div className="output-item">
                        <span className="output-label">Target Ratio Used:</span>
                        <span className="output-value">{outputInfo.targetRatio}</span>
                      </div>
                      <div className="output-item">
                        <span className="output-label">Random State Used:</span>
                        <span className="output-value">{outputInfo.randomState}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="output-placeholder">
                      <p>Output information will appear here after processing</p>
                      <p style={{ fontSize: '0.75rem', marginTop: '0.5rem' }}>Submit the form to see the results</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;