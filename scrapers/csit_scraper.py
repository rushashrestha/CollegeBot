from bs4 import BeautifulSoup
import os
import requests
import pdfkit

class CSITPDFGenerator:
    def __init__(self):
        self.url = "https://samriddhicollege.edu.np/course/bachelor-of-computer-science-and-information-technology-bsc-csit/"
        self.output_dir = "data/scraped_pdfs"
        os.makedirs(self.output_dir, exist_ok=True)  # Create folder if needed
    

    def generate_full_page_pdf(self):
        response = requests.get(self.url)
        if response.status_code != 200:
            print(f"Failed to fetch {self.url}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # Create a new clean document structure
        new_doc = BeautifulSoup("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>CSIT Program Structure</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; }
                .section { margin-bottom: 30px; }
                .highlight-box { border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; background-color: #f9f9f9; }
                h2 { color: #2a6496; border-bottom: 1px solid #eee; padding-bottom: 5px; }
                table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                ul { margin-left: 20px; }
                .career-item { margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px dashed #eee; }
            .career-item:last-child { border-bottom: none; }
            </style>
        </head>
        <body>
        </body>
        </html>
        """, 'html.parser')

        # 1. Process and add program highlights first
        highlights_div = soup.find('div', class_='flex items-center sm:gap-[30px] gap-[20px] flex-wrap')
        if highlights_div:
            science_field = highlights_div.find_all('p')[0].get_text(strip=True)
            graduated_batches = highlights_div.find_all('p')[1].get_text(strip=True)
            total_hours = highlights_div.find_all('p')[2].get_text(strip=True)
            
            highlights_html = f"""
            <div class="highlight-box">
                <h2>Program Highlights</h2>
                <p><strong>Field of Study:</strong> {science_field}</p>
                <p><strong>Alumni:</strong> {graduated_batches}</p>
                <p><strong>Duration:</strong> {total_hours} of instruction</p>
            </div>
            """
            new_doc.body.append(BeautifulSoup(highlights_html, 'html.parser'))

        # 2. Process eligibility criteria
        eligibility_section = soup.find(id='eligibility_criteria')
        if eligibility_section:
            # Clean up eligibility section
            target_paragraphs = eligibility_section.find_all('p', 
                class_='fs-small font-semibold ff-nunito text-white text-center leading-normal')
            for p in target_paragraphs:
                p.decompose()

            # Convert to ordered list
            ol = new_doc.new_tag('ol')
            ul = eligibility_section.find('ul')
            if ul:
                for li in ul.find_all('li'):
                    new_li = new_doc.new_tag('li')
                    new_li.string = li.get_text(strip=True)
                    ol.append(new_li)
            else:
                paragraphs = eligibility_section.find_all('p')
                for p in paragraphs:
                    new_li = new_doc.new_tag('li')
                    new_li.string = p.get_text(strip=True)
                    ol.append(new_li)

            # Create section container
            eligibility_container = new_doc.new_tag('div', **{'class': 'section'})
            header = new_doc.new_tag('h2')
            header.string = 'Eligibility Criteria'
            eligibility_container.append(header)
            eligibility_container.append(ol)
            new_doc.body.append(eligibility_container)

        # 3. Process course outline
        course_outline = soup.find(id="course")
        if course_outline:
            # Create container for course outline
            outline_container = new_doc.new_tag('div', **{'class': 'section'})
            header = new_doc.new_tag('h2')
            header.string = 'Year-wise Course Outline'
            outline_container.append(header)

            # Process semester tables
            for i in range(8):
                year_id = f"course{i}"
                year_content = soup.find(id=year_id)
                if year_content:
                    # Add semester heading
                    year_heading = new_doc.new_tag('h3')
                    year_heading.string = f"Semester {i+1}"
                    outline_container.append(year_heading)

                    # Add table if exists
                    table = year_content.find('table')
                    if table:
                        outline_container.append(table)
                    else:
                        outline_container.append(year_content)

            # Add non-credit courses
            non_credit_section = soup.find('section', id='non_credit_course')
            if non_credit_section:
                non_credit_courses = [card.get_text(strip=True) 
                                    for card in non_credit_section.select('.nonCreditCourse-Card p')]
                
                if non_credit_courses:
                    ncc_heading = new_doc.new_tag('h3')
                    ncc_heading.string = "Non-Credit Courses (NCC):"
                    outline_container.append(ncc_heading)

                    ul = new_doc.new_tag('ul')
                    for course in non_credit_courses:
                        li = new_doc.new_tag('li')
                        li.string = course
                        ul.append(li)
                    outline_container.append(ul)

            new_doc.body.append(outline_container)

        # In the careers section processing:
        careers_section = soup.find('div', class_='samriddhi-carrerAfterCardSlider')
        if not careers_section:
            careers_section = soup.find('section', id='career_opportunities')

        if careers_section:
            # Create container for careers
            careers_container = new_doc.new_tag('div', **{'class': 'section'})
            header = new_doc.new_tag('h2')
            header.string = 'Career Opportunities'
            careers_container.append(header)

            # Find all career cards (both original and cloned slides)
            career_cards = careers_section.find_all(class_='slick-slide')
            
            if not career_cards:
                # Fallback to other selectors if no slick-slide found
                career_cards = careers_section.find_all(class_=lambda x: x and 'rounded-lg border border-[#CECECE]' in x)

            unique_careers = set()  # To avoid duplicates from slider clones
            
            for card in career_cards:
                if 'slick-cloned' in card.get('class', []):
                    continue  # Skip cloned slider elements
                    
                # Extract job title
                title_tag = card.find('h3', class_='ff-nunito fs-regular text-neutral-black font-bold leading-normal')
                if not title_tag:
                    continue
                    
                title = title_tag.get_text(strip=True)
                if title in unique_careers:
                    continue  # Skip duplicates
                    
                unique_careers.add(title)
                
                # Extract job description
                description = ""
                desc_tag = card.find('p', class_='text-[14px] font-medium ff-quicksand text-neutral-black pt-[10px]')
                if desc_tag:
                    description = desc_tag.get_text(strip=True)
                
                # Create career item in our document
                career_div = new_doc.new_tag('div', **{'class': 'career-item'})
                
                title_heading = new_doc.new_tag('h3')
                title_heading.string = title
                career_div.append(title_heading)
                
                if description:
                    desc_para = new_doc.new_tag('p')
                    desc_para.string = description
                    career_div.append(desc_para)
                
                careers_container.append(career_div)
            
            # If no cards found, fall back to processing as plain content
            if not unique_careers:
                # Remove unwanted paragraph if it exists
                for p in careers_section.find_all('p', class_='ff-quicksand fs-small font-medium text-neutral-DarkGray pt-4'):
                    p.decompose()
                
                # Remove all images
                for img in careers_section.find_all('img'):
                    img.decompose()
                    
                # Add remaining content
                text_content = careers_section.get_text(' ', strip=True)
                if text_content:
                    career_div = new_doc.new_tag('div', **{'class': 'career-item'})
                    career_div.string = text_content
                    careers_container.append(career_div)
            
            new_doc.body.append(careers_container)
        # Generate PDF
        output_path = os.path.join(self.output_dir, "full_csit_program.pdf")
        try:
            pdfkit.from_string(
                str(new_doc),
                output_path,
                options={
                    'encoding': 'UTF-8',
                    'page-size': 'A4',
                    'margin-top': '15mm',
                    'quiet': ''
                },
                configuration=pdfkit.configuration(
                    wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
                )
            )
            print(f"PDF successfully generated at {output_path}")
            return output_path
        except Exception as e:
            print(f"Failed to generate PDF: {str(e)}")
            return None
 


if __name__ == "__main__":
    generator = CSITPDFGenerator()
    generator.generate_full_page_pdf()