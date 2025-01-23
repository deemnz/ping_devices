<body>
  <h1>IP Monitoring and Alert System</h1>
    
    <p>This project is a Python-based monitoring tool for tracking the availability of IP addresses and sending notifications via Telegram in case of status changes. The application supports adding, updating, and monitoring objects with flexible configuration options.</p>

    <h2>Features</h2>
    <ul>
        <li>Add, update, and manage monitoring objects.</li>
        <li>Supports single IPs and IP ranges.</li>
        <li>Status logging to SQLite database.</li>
        <li>Notifications sent to Telegram chat(s) on status changes.</li>
        <li>Option to toggle logging for reduced output.</li>
        <li>Runs as a service or manually.</li>
        <li>Handles graceful service termination with confirmation prompts.</li>
    </ul>

    <h2>Prerequisites</h2>
    <ul>
        <li>Python 3.7 or higher</li>
        <li>Required libraries (listed in <code>requirements.txt</code>)</li>
        <li>SQLite3 (for database)</li>
        <li>Root privileges (for ICMP ping)</li>
    </ul>

    <h2>Setup</h2>
    <pre>
    git clone https://github.com/your-repo/ip-monitoring-system.git
    cd ip-monitoring-system
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    </pre>

    <h2>Usage</h2>
    <h3>Start the Application</h3>
    <pre>
    python3 main.py
    </pre>

    <h3>Main Menu Options</h3>
    <ol>
        <li>Add a new monitoring object</li>
        <li>Update an existing monitoring object</li>
        <li>Select and monitor an object</li>
        <li>Stop the service</li>
        <li>Exit</li>
    </ol>

    <h3>Database Structure</h3>
    <p>The application uses a SQLite database with the following tables:</p>
    <ul>
        <li><strong>objects</strong>: Stores object names and configurations.</li>
        <li><strong>ip_names</strong>: Maps IP addresses to user-friendly names.</li>
    </ul>

    <h3>Telegram Bot Integration</h3>
    <p>To use Telegram notifications:</p>
    <ol>
        <li>Create a bot using <a href="https://t.me/botfather">BotFather</a>.</li>
        <li>Obtain the bot token and chat IDs for recipients.</li>
        <li>Configure these details when adding or updating objects.</li>
    </ol>

    <h3>Service as a Background Process</h3>
    <p>Use <code>tmux</code> or <code>screen</code> to run the application as a persistent service:</p>
    <pre>
    tmux new -s ip-monitoring
    python3 main.py
    </pre>

    <h2>Contributing</h2>
    <p>Pull requests are welcome! For major changes, please open an issue first to discuss your ideas.</p>

    <h2>License</h2>
    <p>This project is licensed under the MIT License.</p>
</body>
