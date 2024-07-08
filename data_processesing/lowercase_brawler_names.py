import csv

# Define brawler categories
damage_dealers = ["8-Bit", "Carl", "Chester", "Chuck", "Clancy", "Colette", "Colt", "Eve", 
    "Lola", "Nita", "Pearl", "R-T", "Rico", "Shelly", "Spike", "Surge", "Tara"]

controllers = ["Amber", "Bo", "Jessie", "Lou", "Charlie", "Mr. P", "Emz", "Otis", 
               "Gale", "Sandy", "Gene", "Griff", "Squeak", "Willow", "Penny"]

snipers = ["Angelo", "Bea", "Belle", "Bonnie", "Brock", "Janet", "Maisie", "Mandy",
             "Nani", "Piper"]

throwers = ["Barley", "Dynamike", "Grom", "Larry & Lawrie", "Sprout", "Tick"]

assassins = ["Buzz", "Cordelius", "Crow", "Edgar", "Fang", "Leon", "Lily",
             "Melodie", "Mico", "Mortis", "Sam", "Stu"]

tanks = ["Ash", "Bibi", "Bull", "Buster", "Darryl", "Draco", "El Primo", "Frank",
          "Hank", "Jacky", "Meg", "Rosa"]

supports = ["Berry", "Byron", "Doug", "Gray", "Gus", "Kit", "Max", "Pam", "Poco",
             "Ruffs"]

# Combine all brawlers into a single list and convert to lowercase for comparison
all_brawlers = damage_dealers + controllers + snipers + throwers + assassins + tanks + supports
all_brawlers_lower = {b.lower(): b for b in all_brawlers}

def process_csv(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in reader:
            brawler_id = row['brawler_id'].lower()
            if brawler_id in all_brawlers_lower:
                row['brawler_id'] = all_brawlers_lower[brawler_id]
            writer.writerow(row)

# Usage
input_file = 'important_data/brawler_data.csv'  # Replace with your input CSV file name
output_file = 'output.csv'  # Replace with your desired output CSV file name
process_csv(input_file, output_file)
