# ComicRack CE – Filename Parser (Configurable Regex)

A ComicRack **Community Edition** plugin that parses metadata from **filenames** using **user-configurable regular expressions** (edited via a WinForms UI). It can fill **Number**, **Title**, **Series**, **Year**, **Volume**, and **Custom_** values.

---

## Installation

You can install the plugin in one of two ways:

### Option 1 — Manual installation

1. Download this repository (ZIP or clone).

2. Copy the entire folder into your ComicRack CE scripts directory:

   ```
   `%AppData%\Roaming\cYo\ComicRack Community Edition\Scripts\FilenameParser`
   ```

> Tip: If the Scripts folder doesn’t exist, create it manually.

3. Restart ComicRack CE to load the plugin.

###Option 2 — One-click installation

1. Go to the Releases page.

2. Download the latest `FilenameParser.crplugin`.

3. Double-click the file, and ComicRack CE will install it automatically.

4. Restart ComicRack CE when prompted.

---

## Usage

- **Scripts → Filename Parser: Configure…** (or click the script icon sub-configure-menu)

	Opens the configuration UI where you can:
	- Paste or edit regex patterns (one per line).
	- Toggle options (overwrite, underscores, extensions, zeros).
	- Use the Test field to check your regex before saving.

	**Test field**
	- Enter a sample filename (e.g., `001 - Amazing Spider-Man.cbz`).
	- Click Test.
	- The plugin will run all active regex patterns in order and show you the captured fields (e.g., `number=001, title=Amazing Spider-Man`).
	- This lets you quickly verify if your regex works as intended without running it on your whole library.

- **Automation → Parse from Filename** (or click the script icon) 
	- Select one or more books, then run this command. You’ll see a summary of updated items.

### Options in the UI

- Overwrite non-empty fields (off by default)
- Normalize underscores to spaces (on by default)
- Strip file extension before matching (on by default)
- Strip leading zeros in Number (e.g., `001 → 1`)

---

## Regex “candidate shapes” (priority order)

The plugin tries your patterns **top-to-bottom** and uses the **first** that matches. Named groups become fields:

- `(?P<number>...)` → Number  
- `(?P<title>...)` → Title  
- `(?P<series>...)` → Series  
- `(?P<year>...)` → Year  
- `(?P<volume>...)` → Volume  
- `(?P<custom_anything>...)` → Saved to Custom Values under key `anything`

Here are four example patterns you can keep in your config (you can remove the ones you don’t need):

1. **Number + Title**
   ```regex
   ^(?P<number>\d{1,6})\s*-\s*(?P<title>.+)$
   ```
   - `001 - Amazing Spider-Man` → `number=001`, `title=Amazing Spider-Man`
   - `009 - Wolverine 42` → `number=009`, `title=Wolverine 42`

2. **Number – Series [– Title]**
   ```regex
   ^(?P<number>\d{1,6})\s*-\s*(?P<series>[^-]+?)(?:\s*-\s*(?P<title>.+))?$
   ```
   - `005 - New Avengers - Illuminati Special` → `series=New Avengers`, `title=Illuminati Special`

3. **Number – Series (Year)**
   ```regex
   ^(?P<number>\d{1,6})\s*-\s*(?P<series>.+?)\s*\((?P<year>\d{4})\)$
   ```
   - `021 - Batman (2016)` → `series=Batman`, `year=2016`

4. **Series (VolumeYear) #Number [– Title]**
   ```regex
   ^(?P<series>.+?)\s+\((?P<volume>\d{4})\)\s*#(?P<number>[\dA-Za-z\.]+)(?:\s*-\s*(?P<title>.*))?$
   ```
   - `The Amazing Spider-Man (1963) #529 - Iron Spider` → `series=The Amazing Spider-Man`, `volume=1963`, `number=529`, `title=Iron Spider`

> Tip: Because the script stops at the **first** match, put your **most common** shape at the top.
