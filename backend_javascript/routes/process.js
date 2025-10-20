// routes/process.js
const express = require('express');
const multer = require('multer');
const FormData = require('form-data');
const axios = require('axios');
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });
const authMiddleware = require('../middleware/auth');

const router = express.Router();

const storage = multer.memoryStorage();
const upload = multer({
  storage,
  limits: { fileSize: 100 * 1024 * 1024 }, // 100MB
  fileFilter: (req, file, cb) => {
    if (file.originalname.endsWith('.zip')) cb(null, true);
    else cb(new Error('Only .zip files are allowed'));
  },
});

router.post('/', authMiddleware, upload.single('zipFile'), async (req, res) => {
  const reqId = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  console.log(`[${reqId}] Request received: POST /process (zipFile=${req.file?.originalname || 'none'})`);

  try {
    if (!req.file) {
      console.warn(`[${reqId}] Validation failed: no file uploaded`);
      return res.status(400).json({ message: 'No file uploaded' });
    }

    const { k_neighbour, target_ratio, random_state } = req.body;
    console.log(
      `[${reqId}] Params received: k_neighbour=${k_neighbour}, target_ratio=${target_ratio}, random_state=${random_state}`
    );

    const kNeighbour = parseInt(k_neighbour, 10);
    if (Number.isNaN(kNeighbour) || kNeighbour < 2) {
      console.warn(`[${reqId}] Validation failed: k_neighbour invalid`);
      return res.status(400).json({ message: 'k_neighbour must be greater than 1' });
    }
    const randomState = parseInt(random_state, 10);
    if (Number.isNaN(randomState)) {
      console.warn(`[${reqId}] Validation failed: random_state invalid`);
      return res.status(400).json({ message: 'random_state must be a valid integer' });
    }
    let targetRatio = null;
    if (target_ratio && target_ratio !== 'null' && target_ratio !== '') {
      const parsed = parseFloat(target_ratio);
      if (Number.isNaN(parsed) || parsed < 0.0 || parsed > 1.0) {
        console.warn(`[${reqId}] Validation failed: target_ratio out of range`);
        return res.status(400).json({ message: 'target_ratio must be between 0.0 and 1.0' });
      }
      targetRatio = parsed;
    }

    // POST /params 
    try {
      console.log(
        `[${reqId}] → Sending /params to Python: kneighbors=${kNeighbour}, targetratio=${targetRatio}, randomstate=${randomState}`
      );
      const headers = { 'Content-Type': 'application/json' };
      if (process.env.PY_API_KEY) headers['X-API-Key'] = process.env.PY_API_KEY;

      const paramsPayload = {
        data: {
          kneighbors: kNeighbour,
          targetratio: targetRatio,
          randomstate: randomState,
        },
      };

      await axios.post('http://localhost:8080/params', paramsPayload, {
        headers,
        timeout: 30000,
      });
      console.log(`[${reqId}]  /params acknowledged by Python`);
    } catch (error) {
      console.error(
        `[${reqId}]  Error sending /params: ${error.message} (status=${error.response?.status || 'n/a'})`
      );
      if (error.code === 'ECONNREFUSED') {
        return res.status(503).json({ message: 'Processing server is not available' });
      }
      const msg =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Failed to send parameters to processing server';
      return res.status(500).json({ message: msg });
    }

    //POST /upload/zip with multipart key "file"
    let assets = [];
    try {
      console.log(
        `[${reqId}]  Uploading ZIP to /upload/zip: filename=${req.file.originalname}, size=${req.file.size} bytes`
      );
      const formData = new FormData();
      formData.append('file', req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype || 'application/zip',
      });

      const headers = { ...formData.getHeaders() };
      if (process.env.PY_API_KEY) headers['X-API-Key'] = process.env.PY_API_KEY;

      const startedAt = Date.now();
      const zipResponse = await axios.post('http://localhost:8080/upload/zip', formData, {
        headers,
        maxContentLength: Infinity,
        maxBodyLength: Infinity,
        timeout: 60000,
      });
      const durationMs = Date.now() - startedAt;

      if (!zipResponse.data || !Array.isArray(zipResponse.data.assets) || zipResponse.data.assets.length === 0) {
        console.warn(`[${reqId}]  /upload/zip returned no assets`);
        return res.status(502).json({ message: 'Invalid response from processing server (/upload/zip)' });
      }
      assets = zipResponse.data.assets;

      const missingId = assets.find((a) => !a.id);
      if (missingId) {
        console.warn(`[${reqId}]  /upload/zip response missing asset id`);
        return res.status(502).json({ message: 'Missing asset id from processing server' });
      }

      const ids = assets.map((a) => a.id).join(', ');
      console.log(
        `[${reqId}]  /upload/zip OK in ${durationMs} ms — assets=${assets.length} [${ids}]`
      );
    } catch (error) {
      console.error(
        `[${reqId}]  Error uploading ZIP: ${error.message} (status=${error.response?.status || 'n/a'})`
      );
      if (error.code === 'ECONNREFUSED') {
        return res.status(503).json({ message: 'Processing server is not available' });
      }
      const detail =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Failed to send zip file to processing server';
      return res.status(500).json({ message: detail });
    }

    // 3) POST /augment/smote with all asset_ids and options
    try {
      const images = assets.map((a) => ({ asset_id: a.id }));
      const payload = {
        images,
        options: { horizontal_flip: false, rotate_deg: null },
      };

      const headers = { 'Content-Type': 'application/json' };
      if (process.env.PY_API_KEY) headers['X-API-Key'] = process.env.PY_API_KEY;

      console.log(
        `[${reqId}]  Requesting augmentation /augment/smote for ${images.length} assets`
      );

      const startedAt = Date.now();
      const augResponse = await axios.post('http://localhost:8080/augment/smote', payload, {
        headers,
        responseType: 'stream', // streaming ZIP
        timeout: 300000,
      });
      const durationMs = Date.now() - startedAt;

      // Pass through headers for file download
      const ct = augResponse.headers['content-type'];
      if (ct) res.setHeader('Content-Type', ct);
      const cd = augResponse.headers['content-disposition'];
      if (cd) {
        res.setHeader('Content-Disposition', cd);
      } else {
        res.setHeader('Content-Disposition', 'attachment; filename="augmented_dataset.zip"');
      }
      const cl = augResponse.headers['content-length'];
      if (cl) res.setHeader('Content-Length', cl);

      console.log(
        `[${reqId}]  /augment/smote responded in ${durationMs} ms — streaming ZIP to client`
      );

      augResponse.data.on('error', (err) => {
        console.error(`[${reqId}]  Stream error (augment zip → client): ${err.message}`);
        if (!res.headersSent) {
          res.status(502).end('Error streaming augmented zip');
        } else {
          res.destroy(err);
        }
      });
      res.on('error', () => {
        console.error(`[${reqId}] Client connection error while streaming`);
        augResponse.data.destroy();
      });
      res.on('close', () => {
        console.log(`[${reqId}] Client connection closed`);
      });
      res.on('finish', () => {
        console.log(`[${reqId}]  Response finished (augmented ZIP sent)`);
      });

      augResponse.data.pipe(res);
    } catch (error) {
      const status = error.response?.status || 'n/a';
      const body = error.response?.data
        ? typeof error.response.data === 'string'
          ? error.response.data
          : JSON.stringify(error.response.data)
        : 'no body';
      console.error(
        `[${reqId}]  Error during augmentation: ${error.message} (status=${status}) body=${body}`
      );

      if (error.response?.status === 404) {
        return res.status(404).json({ message: 'Asset not found for augmentation' });
      }
      if (error.code === 'ECONNREFUSED') {
        return res.status(503).json({ message: 'Processing server is not available' });
      }
      const detail =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Failed to augment dataset';
      return res.status(422).json({ message: detail });
    }
  } catch (error) {
    console.error(`[${reqId}]  Unhandled route error:`, error);
    return res.status(500).json({ message: 'Server error' });
  }
});

module.exports = router;
