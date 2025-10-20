GarvMandloi_231IT023

This zip files contains everyone's contribution, I have listed my individual contribution below.

(requirements-> python3, node 22.4 LTS)
How to run:
1)Inside the smote directory, run "npm i && npm run dev". This will run the react frontend, leave this terminal running.
2)Change directory to "backend" via "cd backend_javascript" and run "npm i && node server.js", also leave this terminal running.
3)Now change directory to "backend_python", and create a virtual environment using "python3 -m venv .venv", use it by 
  "source .venv/bin/activate", and then install dependencies using "python -m pip install -r requirements.txt", and then
  finally run the python server using "uvicorn main:app --host 0.0.0.0 --port 8080 --reload"

-To test the javascript backend, "cd test_javascript_backend" and run the file using "test-process.js". Once all
 the tests are completed a "process-test-summary.csv" will be created. Please ensure "invalid-input.zip" &
 "valid-input.zip" is present in the folder before starting tests.


-Please ensure the react client is running on port 5173 and node server is running on port 5000 and python server is running on 8080.
-Please ensure you are NOT connected to NITK-NET because it prevents connection
to cloud atlas database.

Files/Folders implemented by GarvMandloi_231IT023:
[Couldn't change the file names themselves because it will create troubles with import]
(all paths relative to root)
./backend_javascript/server.js (main server that listens to connections)
./backend_javascript/models/User.js (defines the user schema)
./backend_javascript/config/db.js (connects to cloud atlas database)
./backend_javascript/routes/auth.js (this binds all the functions from the below module to create a route and creates API endpoints)
./backend_javascript/routes/auth (this folder included all the functions from 1.1 in DFD and a few extra ones)
    From the DFD:
    ->recive-credential.js
    ->validate-input.js
    ->issue-jwt-token.js
    ->apply-middleware.js
    Helper functions:
    ->create-user.js (before issuing jwt token, register him in DB if it's a new user)
    ->verify-user.js (before issuing jwt token, verify with DB if it's an existing user)
./backend_python/params (DFD 1.2, makes a FastAPI route to recive parameters and stores them)
    ->router.py 
    ->schemas.py
    ->service.py
./test_javascript_backend
API endpoints created:
  -> /login : allows for login via POST on this endpoint
  -> /register : allows for register via POST on this endpoint
  -> /user : verifies JWT token and returns user details from DB upon 	
	     successful verification.
  -> /process : processes the user's request to apply SMOTE with the given parameters and forwards it to python engine
              upon validation and verification and then returns the output zip to user upon completition 

-Please find all output screenshots within 231IT023_GarvMandloi_Outputs, all integration test realted outputs are 
 within "test_javascript_backend" directory.







