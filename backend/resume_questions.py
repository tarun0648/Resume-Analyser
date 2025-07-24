import json
import os
import logging
from typing import Dict, Any, Optional
from anthropic import Anthropic
from config import CLAUDE_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_interview_questions(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate interview questions based on resume data using Claude AI
    
    Args:
        resume_data: Dictionary containing parsed resume data
        
    Returns:
        Dictionary containing generated interview questions
    """
    logger.info("Generating interview questions based on resume data")
    
    try:
        # Initialize Claude client
        client = Anthropic(api_key=CLAUDE_API_KEY)
        
        # Extract key information for context
        personal_info = resume_data.get('personal_information', {})
        work_experience = resume_data.get('work_experience', [])
        education = resume_data.get('education', [])
        skills = resume_data.get('skills', [])
        projects = resume_data.get('projects', [])
        
        # Create context summary
        context_summary = f"""
        Candidate: {personal_info.get('name', 'Unknown')}
        Skills: {', '.join(skills) if skills else 'Not specified'}
        Experience: {len(work_experience)} work experiences
        Education: {len(education)} educational qualifications
        Projects: {len(projects)} projects
        """
        
        # Construct the prompt
        prompt = f"""
        You are an expert technical interviewer with experience in evaluating candidates across various roles and industries.
        
        Based on the following resume data, generate 10 thoughtful and relevant interview questions that would help assess this candidate's:
        1. Technical skills and competencies
        2. Problem-solving abilities
        3. Communication and teamwork skills
        4. Leadership and initiative
        5. Cultural fit and motivation
        
        Resume Context:
        {context_summary}
        
        Detailed Resume Data:
        {json.dumps(resume_data, indent=2)}
        
        Generate questions that are:
        - Specific to the candidate's background and experience
        - Appropriate for their level of seniority
        - Balanced between technical and behavioral aspects
        - Open-ended to encourage detailed responses
        - Relevant to their industry and role type
        
        Return the response as a JSON object with the following structure:
        {{
            "questions": [
                {{
                    "question": "Question text here",
                    "category": "technical|behavioral|experience|situational",
                    "focus_area": "specific skill or experience area being assessed",
                    "difficulty": "entry|mid|senior",
                    "expected_response_type": "brief description of what a good answer would demonstrate"
                }}
            ],
            "interview_notes": {{
                "candidate_strengths": ["list of key strengths to explore"],
                "areas_to_probe": ["list of areas that need deeper exploration"],
                "recommended_follow_ups": ["suggested follow-up questions or topics"]
            }}
        }}
        
        Respond with valid JSON only, no additional text.
        """
        
        # Call Claude API
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=3000,
            temperature=0.7,
            system="You are an expert interviewer who creates tailored interview questions based on candidate resumes. Return valid JSON only.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract response
        response_text = message.content[0].text
        logger.info("Received response from Claude API")
        
        # Parse JSON response
        try:
            # Try to parse the whole response as JSON
            questions_data = json.loads(response_text)
            logger.info(f"Successfully generated {len(questions_data.get('questions', []))} interview questions")
            return questions_data
            
        except json.JSONDecodeError:
            logger.warning("Initial JSON parsing failed, attempting to extract JSON from response")
            # Try to extract JSON from code blocks
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                try:
                    questions_data = json.loads(json_match.group(1))
                    logger.info(f"Successfully extracted {len(questions_data.get('questions', []))} interview questions")
                    return questions_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON: {e}")
                    return create_fallback_questions(resume_data)
            else:
                logger.error("Could not find JSON block in response")
                return create_fallback_questions(resume_data)
                
    except Exception as e:
        logger.error(f"Error generating interview questions: {e}")
        return create_fallback_questions(resume_data)

def create_fallback_questions(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create fallback interview questions when AI generation fails
    
    Args:
        resume_data: Dictionary containing parsed resume data
        
    Returns:
        Dictionary containing fallback interview questions
    """
    logger.info("Creating fallback interview questions")
    
    # Extract basic info
    skills = resume_data.get('skills', [])
    work_exp = resume_data.get('work_experience', [])
    projects = resume_data.get('projects', [])
    
    # Determine experience level
    exp_level = "entry"
    if len(work_exp) > 3:
        exp_level = "senior"
    elif len(work_exp) > 1:
        exp_level = "mid"
    
    # Create basic questions
    questions = []
    
    # General questions
    questions.extend([
        {
            "question": "Can you walk me through your professional background and what led you to your current career path?",
            "category": "experience",
            "focus_area": "career progression",
            "difficulty": exp_level,
            "expected_response_type": "Career narrative showing growth and decision-making"
        },
        {
            "question": "What motivates you in your work, and what type of environment do you thrive in?",
            "category": "behavioral",
            "focus_area": "motivation and culture fit",
            "difficulty": "entry",
            "expected_response_type": "Self-awareness and alignment with company values"
        }
    ])
    
    # Technical questions based on skills
    if skills:
        top_skills = skills[:3]  # Focus on first 3 skills
        for skill in top_skills:
            questions.append({
                "question": f"How would you describe your experience with {skill}? Can you give me an example of a challenging project where you used this skill?",
                "category": "technical",
                "focus_area": skill,
                "difficulty": exp_level,
                "expected_response_type": f"Specific examples demonstrating {skill} proficiency"
            })
    
    # Experience-based questions
    if work_exp:
        questions.extend([
            {
                "question": "Tell me about a time when you had to solve a complex problem at work. How did you approach it?",
                "category": "situational",
                "focus_area": "problem-solving",
                "difficulty": exp_level,
                "expected_response_type": "STAR method response showing analytical thinking"
            },
            {
                "question": "Describe a situation where you had to work with a difficult team member or stakeholder. How did you handle it?",
                "category": "behavioral",
                "focus_area": "interpersonal skills",
                "difficulty": "mid",
                "expected_response_type": "Conflict resolution and communication skills"
            }
        ])
    
    # Project-based questions
    if projects:
        questions.append({
            "question": "I see you worked on several projects. Can you tell me about one that you're particularly proud of and the impact it had?",
            "category": "experience",
            "focus_area": "project management",
            "difficulty": exp_level,
            "expected_response_type": "Project ownership and impact measurement"
        })
    
    # Leadership questions for senior candidates
    if exp_level == "senior":
        questions.extend([
            {
                "question": "Tell me about a time when you had to lead a team or mentor junior colleagues. What was your approach?",
                "category": "behavioral",
                "focus_area": "leadership",
                "difficulty": "senior",
                "expected_response_type": "Leadership philosophy and concrete examples"
            },
            {
                "question": "How do you stay current with industry trends and continue learning in your field?",
                "category": "behavioral",
                "focus_area": "continuous learning",
                "difficulty": "senior",
                "expected_response_type": "Learning strategies and industry awareness"
            }
        ])
    
    # Generic closing questions
    questions.extend([
        {
            "question": "What are your career goals for the next 2-3 years, and how does this role fit into those plans?",
            "category": "behavioral",
            "focus_area": "career goals",
            "difficulty": "entry",
            "expected_response_type": "Career planning and role alignment"
        },
        {
            "question": "Do you have any questions about our company, team, or the role itself?",
            "category": "behavioral",
            "focus_area": "engagement and interest",
            "difficulty": "entry",
            "expected_response_type": "Thoughtful questions showing genuine interest"
        }
    ])
    
    # Limit to 10 questions
    questions = questions[:10]
    
    return {
        "questions": questions,
        "interview_notes": {
            "candidate_strengths": [
                f"Has {len(work_exp)} work experiences" if work_exp else "Early career candidate",
                f"Skills in {', '.join(skills[:3])}" if skills else "Developing technical skills",
                f"Project experience in {len(projects)} projects" if projects else "Building project portfolio"
            ],
            "areas_to_probe": [
                "Technical depth and problem-solving approach",
                "Communication and teamwork abilities",
                "Growth mindset and learning agility",
                "Cultural fit and motivation"
            ],
            "recommended_follow_ups": [
                "Ask for specific examples with metrics",
                "Probe for lessons learned from failures",
                "Explore collaboration and communication style",
                "Understand learning and development interests"
            ]
        }
    }

def run_generation_with_args(resume_file_path: str, output_file_path: str) -> Dict[str, Any]:
    """
    Main function to generate interview questions from a resume file
    
    Args:
        resume_file_path: Path to the JSON resume file
        output_file_path: Path where to save the generated questions
        
    Returns:
        Dictionary containing generated interview questions
    """
    try:
        logger.info(f"Processing resume file: {resume_file_path}")
        
        # Read resume data from file
        with open(resume_file_path, 'r', encoding='utf-8') as file:
            resume_data = json.load(file)
        
        # Generate interview questions
        questions_data = generate_interview_questions(resume_data)
        
        # Save to output file
        with open(output_file_path, 'w', encoding='utf-8') as file:
            json.dump(questions_data, file, indent=2)
        
        logger.info(f"Interview questions saved to: {output_file_path}")
        return questions_data
        
    except FileNotFoundError:
        logger.error(f"Resume file not found: {resume_file_path}")
        return {"error": f"Resume file not found: {resume_file_path}"}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in resume file: {resume_file_path}")
        return {"error": f"Invalid JSON in resume file: {resume_file_path}"}
    except Exception as e:
        logger.error(f"Error processing resume: {e}")
        return {"error": f"Error processing resume: {str(e)}"}

def main():
    """
    Main function for command-line usage
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate interview questions from resume')
    parser.add_argument('resume_file', help='Path to the JSON resume file')
    parser.add_argument('output_file', help='Path to save the generated questions')
    
    args = parser.parse_args()
    
    result = run_generation_with_args(args.resume_file, args.output_file)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1
    else:
        print(f"Successfully generated {len(result.get('questions', []))} interview questions")
        return 0

if __name__ == "__main__":
    exit(main())