# **Heal Bot**

The only multipurpose, aesthetic bot you'll ever need in your servers! It has a range of features, including:

- Music
- Moderation
- Fun
- & More

## **Requirements**

- Python 3.11
- PostgreSQL
- Basic understanding of the terminal

## **Getting Started**

1. **Clone the Repository:**
   To get started, run the following command:

   ```bash
   git clone https://github.com/hiddeout/heal.git
   ```

2. **Install PostgreSQL:**
   Download and install PostgreSQL from [here](https://www.postgresql.org/download/windows/) or for your OS of choice.

3. **Create a Database:**
   Run the following command in your terminal or CMD:

   - For Linux:
     ```bash
     sudo -U postgres psql
     ```
   - For Windows:
     ```bash
     psql -U postgres
     ```

   Then inside the postgres terminal, run:

   ```sql
   CREATE DATABASE dev;
   ```

## **Important**

- Make sure to fill out the `.env` file with your Discord bot `token` and `LOG_CHANNEL_ID` with your channel ID.
- Edit line 21 and 36 in `/heal/events/healboost.py` with the guild and role of your choice.
- Make sure to edit line 39 of `heal.py` to replace your Discord owner ID.
- Ensure Python (version 311) is installed and added to your path if you're on Windows. You can check the version by running:
  ```bash
  python --version
  ```

## **Install the Dependencies**

Open a terminal in this directory and run:

```bash
pip install -r requirements.txt
```

If this fails on windows make sure Python is installed and added to PATH.

Once installed, run:

```bash
python main.py
```

Feel free to fork this and edit it however you want meow
