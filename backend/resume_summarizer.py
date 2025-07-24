import json
import os
import logging
import requests
from typing import Dict, Any, Optional, Tuple
from config import CLAUDE_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaudeHTTPClient:
    """
    HTTP-based Claude client to avoid library conflicts
    """
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def messages_create(self, model, max_tokens, system=None, messages=None, temperature=None):
        """Create a message using direct HTTP request"""
        url = f"{self.base_url}/messages"
        
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages or []
        }
        
        if system:
            payload["system"] = system
        
        if temperature is not None:
            payload["temperature"] = temperature
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            
            # Create a simple response object that mimics the anthropic client response
            class SimpleResponse:
                def __init__(self, data):
                    self.content = [SimpleContent(data["content"][0]["text"])]
            
            class SimpleContent:
                def __init__(self, text):
                    self.text = text
            
            return SimpleResponse(data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request to Claude API failed: {e}")
            raise Exception(f"Claude API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Claude API call: {e}")
            raise

def compare_resume_with_job(resume_data: Dict[str, Any], job_description: str) -> Optional[Dict[str, Any]]:
    """
    Compare a resume with a job description using Claude AI to generate a match analysis.
    
    Args:
        resume_data: Dictionary containing parsed resume data
        job_description: String containing the job description
        
    Returns:
        Dictionary containing match analysis or None if there was an error
    """
    logger.info("Starting resume comparison with job description")
    
    try:
        # Initialize Claude client with HTTP approach
        client = ClaudeHTTPClient(CLAUDE_API_KEY)
        
        # Extract key information from resume for better analysis
        personal_info = resume_data.get('personal_information', {})
        work_experience = resume_data.get('work_experience', [])
        education = resume_data.get('education', [])
        skills = resume_data.get('skills', [])
        projects = resume_data.get('projects', [])
        certifications = resume_data.get('certifications', [])
        
        # Create a summary of candidate profile
        candidate_summary = f"""
        Candidate: {personal_info.get('name', 'Unknown')}
        Skills: {', '.join(skills) if skills else 'Not specified'}
        Years of Experience: {len(work_experience)} positions
        Education Level: {len(education)} qualifications
        Project Experience: {len(projects)} projects
        Certifications: {len(certifications)} certifications
        """
        
        # Construct the comprehensive prompt for Claude
        prompt = f"""
        You are an expert hiring manager and talent evaluator with 15+ years of experience in recruitment across multiple industries. You have a deep understanding of what makes candidates successful in various roles.

        Your task is to analyze how well a candidate's resume matches a specific job description. You should evaluate the candidate holistically, considering not just technical skills but also experience level, cultural fit indicators, growth potential, and overall suitability.

        **JOB DESCRIPTION:**
        {job_description}

        **CANDIDATE PROFILE SUMMARY:**
        {candidate_summary}

        **DETAILED RESUME DATA:**
        {json.dumps(resume_data, indent=2)}

        **ANALYSIS FRAMEWORK:**
        Please analyze the following dimensions:

        1. **Technical Skills Match**: How well do the candidate's technical skills align with job requirements?
        2. **Experience Relevance**: Is their work experience relevant to the role and industry?
        3. **Education Alignment**: Does their educational background support the role requirements?
        4. **Seniority Level**: Does their experience level match what the role demands?
        5. **Industry Experience**: Do they have relevant industry/domain knowledge?
        6. **Project Complexity**: Have they worked on projects of similar scope/complexity?
        7. **Leadership/Growth**: Do they show progression and leadership potential?
        8. **Cultural Indicators**: Based on their background, do they show traits that align with typical role expectations?

        **SCORING GUIDELINES:**
        - 90-100: Exceptional match - candidate exceeds most requirements with strong additional value
        - 75-89: Strong match - candidate meets most key requirements with minor gaps
        - 60-74: Good match - candidate meets core requirements but has some notable gaps
        - 40-59: Moderate match - candidate has relevant background but significant gaps exist
        - 20-39: Weak match - limited alignment with role requirements
        - 0-19: Poor match - minimal overlap with job requirements

        **OUTPUT FORMAT:**
        Return a JSON object with exactly this structure:
        {{
            "match_score": <number between 0-100>,
            "match_label": "<Excellent Match|Good Match|Moderate Match|Poor Match|Very Poor Match>",
            "summary": "<2-3 sentence overall assessment>",
            "strengths": [
                "<specific strength 1>",
                "<specific strength 2>",
                "<specific strength 3>",
                "<specific strength 4>",
                "<specific strength 5>"
            ],
            "gaps": [
                "<specific gap or concern 1>",
                "<specific gap or concern 2>",
                "<specific gap or concern 3>",
                "<specific gap or concern 4>"
            ],
            "detailed_analysis": {{
                "technical_skills": {{
                    "score": <0-100>,
                    "assessment": "<brief assessment>"
                }},
                "experience_relevance": {{
                    "score": <0-100>,
                    "assessment": "<brief assessment>"
                }},
                "education_alignment": {{
                    "score": <0-100>,
                    "assessment": "<brief assessment>"
                }},
                "seniority_match": {{
                    "score": <0-100>,
                    "assessment": "<brief assessment>"
                }}
            }},
            "recommendations": [
                "<actionable recommendation 1>",
                "<actionable recommendation 2>",
                "<actionable recommendation 3>"
            ],
            "interview_focus_areas": [
                "<area to explore in interview 1>",
                "<area to explore in interview 2>",
                "<area to explore in interview 3>"
            ]
        }}

        **IMPORTANT GUIDELINES:**
        - Be specific and evidence-based in your analysis
        - Reference actual skills, experiences, and qualifications from the resume
        - Consider both hard skills and soft skills indicators
        - Be constructive in identifying gaps - suggest ways to address them
        - Provide actionable insights for hiring decisions
        - Consider the candidate's potential for growth, not just current state

        Return ONLY the JSON object, no additional text or explanations.
        """

        # Call Claude API
        message = client.messages_create(
            model="claude-3-opus-20240229",
            max_tokens=3000,
            temperature=0.3,  # Lower temperature for more consistent analysis
            system="You are an expert hiring manager who provides detailed, fair, and constructive candidate evaluations. Always return valid JSON.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract content from Claude's response
        response_text = message.content[0].text
        logger.info("Received response from Claude API")
        
        # Parse JSON response
        try:
            # Try to parse the whole response as JSON
            analysis = json.loads(response_text)
            logger.info(f"Successfully generated resume analysis with match score: {analysis.get('match_score', 'N/A')}")
            return analysis
            
        except json.JSONDecodeError:
            logger.warning("Initial JSON parsing failed, attempting to extract JSON from response")
            # Try to extract JSON from code blocks
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                try:
                    analysis = json.loads(json_match.group(1))
                    logger.info(f"Successfully extracted resume analysis with match score: {analysis.get('match_score', 'N/A')}")
                    return analysis
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON: {e}")
                    return create_fallback_analysis(resume_data, job_description)
            else:
                logger.error("Could not find JSON block in response")
                return create_fallback_analysis(resume_data, job_description)
                
    except Exception as e:
        logger.error(f"Error in resume comparison: {e}")
        return create_fallback_analysis(resume_data, job_description)

def create_fallback_analysis(resume_data: Dict[str, Any], job_description: str) -> Dict[str, Any]:
    """
    Create a basic fallback analysis when AI analysis fails
    
    Args:
        resume_data: Dictionary containing parsed resume data
        job_description: String containing the job description
        
    Returns:
        Dictionary containing basic match analysis
    """
    logger.info("Creating fallback analysis")
    
    # Extract basic information
    skills = resume_data.get('skills', [])
    work_exp = resume_data.get('work_experience', [])
    education = resume_data.get('education', [])
    projects = resume_data.get('projects', [])
    
    # Simple keyword matching for basic analysis
    job_lower = job_description.lower()
    resume_skills_lower = [skill.lower() for skill in skills]
    
    # Count skill matches
    skill_matches = sum(1 for skill in resume_skills_lower if skill in job_lower)
    skill_match_ratio = skill_matches / max(len(skills), 1) if skills else 0
    
    # Basic scoring logic
    base_score = 40  # Base score
    
    # Add points for experience
    if len(work_exp) > 0:
        base_score += min(len(work_exp) * 10, 30)
    
    # Add points for education
    if len(education) > 0:
        base_score += min(len(education) * 5, 15)
    
    # Add points for skills match
    base_score += skill_match_ratio * 30
    
    # Add points for projects
    if len(projects) > 0:
        base_score += min(len(projects) * 5, 15)
    
    # Cap at 100
    match_score = min(base_score, 100)
    
    # Determine match label
    if match_score >= 80:
        match_label = "Good Match"
    elif match_score >= 60:
        match_label = "Moderate Match"
    elif match_score >= 40:
        match_label = "Poor Match"
    else:
        match_label = "Very Poor Match"
    
    return {
        "match_score": int(match_score),
        "match_label": match_label,
        "summary": f"Basic analysis shows a {match_label.lower()} based on {len(work_exp)} work experiences, {len(skills)} listed skills, and {skill_matches} skill matches with the job description.",
        "strengths": [
            f"Has {len(work_exp)} work experiences" if work_exp else "Entry-level candidate",
            f"Lists {len(skills)} relevant skills" if skills else "Developing skill set",
            f"Educational background with {len(education)} qualifications" if education else "Building educational foundation",
            f"Project experience with {len(projects)} projects" if projects else "Gaining practical experience",
            "Potential for growth and development"
        ][:5],
        "gaps": [
            "Limited skill alignment analysis due to processing constraints",
            "Detailed experience relevance needs manual review",
            "Industry-specific requirements need closer evaluation",
            "Soft skills assessment requires interview evaluation"
        ],
        "detailed_analysis": {
            "technical_skills": {
                "score": int(skill_match_ratio * 100),
                "assessment": f"Found {skill_matches} potential skill matches"
            },
            "experience_relevance": {
                "score": min(len(work_exp) * 25, 100),
                "assessment": f"Has {len(work_exp)} work experiences"
            },
            "education_alignment": {
                "score": min(len(education) * 50, 100),
                "assessment": f"Has {len(education)} educational qualifications"
            },
            "seniority_match": {
                "score": 50,
                "assessment": "Requires manual evaluation"
            }
        },
        "recommendations": [
            "Conduct detailed technical interview to assess skills",
            "Review specific project experiences for relevance",
            "Evaluate cultural fit through behavioral questions"
        ],
        "interview_focus_areas": [
            "Technical competency validation",
            "Problem-solving approach",
            "Communication and teamwork skills"
        ]
    }

def resume_job_match_analysis(resume_file_path: str, job_description: str) -> Optional[Dict[str, Any]]:
    """
    Process a resume file and compare it with a job description.
    
    Args:
        resume_file_path: Path to the JSON resume file
        job_description: String containing the job description
        
    Returns:
        Dictionary containing match analysis or None if there was an error
    """
    try:
        logger.info(f"Processing resume file: {resume_file_path}")
        
        # Validate inputs
        if not job_description or not job_description.strip():
            logger.warning("No job description provided")
            return None
        
        # Read resume data from file
        with open(resume_file_path, 'r', encoding='utf-8') as file:
            resume_data = json.load(file)
        
        # Validate resume data
        if not isinstance(resume_data, dict):
            logger.error("Invalid resume data format")
            return None
        
        # Compare resume with job description
        result = compare_resume_with_job(resume_data, job_description)
        
        return result
        
    except FileNotFoundError:
        logger.error(f"Resume file not found: {resume_file_path}")
        return {"error": f"Resume file not found: {resume_file_path}"}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in resume file: {resume_file_path}")
        return {"error": f"Invalid JSON in resume file: {resume_file_path}"}
    except Exception as e:
        logger.error(f"Error processing resume: {e}")
        return {"error": f"Error processing resume: {str(e)}"}

def batch_resume_analysis(resume_files: list, job_description: str) -> Dict[str, Any]:
    """
    Analyze multiple resumes against a single job description
    
    Args:
        resume_files: List of paths to JSON resume files
        job_description: String containing the job description
        
    Returns:
        Dictionary containing batch analysis results
    """
    logger.info(f"Starting batch analysis of {len(resume_files)} resumes")
    
    results = []
    successful_analyses = 0
    failed_analyses = 0
    
    for resume_file in resume_files:
        try:
            analysis = resume_job_match_analysis(resume_file, job_description)
            if analysis and 'error' not in analysis:
                analysis['resume_file'] = resume_file
                results.append(analysis)
                successful_analyses += 1
            else:
                failed_analyses += 1
                logger.warning(f"Failed to analyze: {resume_file}")
        except Exception as e:
            failed_analyses += 1
            logger.error(f"Error analyzing {resume_file}: {e}")
    
    # Sort results by match score (highest first)
    results.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    
    return {
        "total_resumes": len(resume_files),
        "successful_analyses": successful_analyses,
        "failed_analyses": failed_analyses,
        "top_candidates": results[:10],  # Top 10 candidates
        "all_results": results,
        "summary_stats": {
            "highest_score": results[0].get('match_score', 0) if results else 0,
            "lowest_score": results[-1].get('match_score', 0) if results else 0,
            "average_score": sum(r.get('match_score', 0) for r in results) / len(results) if results else 0
        }
    }

def generate_hiring_report(analysis_results: Dict[str, Any], job_title: str = "Position") -> str:
    """
    Generate a comprehensive hiring report based on analysis results
    
    Args:
        analysis_results: Results from resume_job_match_analysis
        job_title: Title of the position being evaluated
        
    Returns:
        Formatted hiring report as string
    """
    if not analysis_results or 'error' in analysis_results:
        return "Unable to generate report due to analysis errors."
    
    report = f"""
# HIRING ANALYSIS REPORT
## Position: {job_title}

### OVERALL MATCH ASSESSMENT
- **Match Score**: {analysis_results.get('match_score', 'N/A')}/100
- **Match Level**: {analysis_results.get('match_label', 'Unknown')}
- **Overall Assessment**: {analysis_results.get('summary', 'No summary available')}

### KEY STRENGTHS
"""
    
    strengths = analysis_results.get('strengths', [])
    for i, strength in enumerate(strengths, 1):
        report += f"{i}. {strength}\n"
    
    report += "\n### AREAS OF CONCERN\n"
    gaps = analysis_results.get('gaps', [])
    for i, gap in enumerate(gaps, 1):
        report += f"{i}. {gap}\n"
    
    detailed = analysis_results.get('detailed_analysis', {})
    if detailed:
        report += "\n### DETAILED BREAKDOWN\n"
        for category, details in detailed.items():
            category_name = category.replace('_', ' ').title()
            score = details.get('score', 'N/A')
            assessment = details.get('assessment', 'No assessment')
            report += f"- **{category_name}**: {score}/100 - {assessment}\n"
    
    recommendations = analysis_results.get('recommendations', [])
    if recommendations:
        report += "\n### RECOMMENDATIONS\n"
        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"
    
    interview_areas = analysis_results.get('interview_focus_areas', [])
    if interview_areas:
        report += "\n### INTERVIEW FOCUS AREAS\n"
        for i, area in enumerate(interview_areas, 1):
            report += f"{i}. {area}\n"
    
    return report

# Command line interface
def main():
    """Command line interface for resume analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze resume against job description')
    parser.add_argument('resume_file', help='Path to JSON resume file')
    parser.add_argument('job_description', help='Job description text or file path')
    parser.add_argument('--output', '-o', help='Output file for analysis results')
    parser.add_argument('--report', '-r', help='Generate hiring report')
    
    args = parser.parse_args()
    
    # Read job description
    if os.path.isfile(args.job_description):
        with open(args.job_description, 'r') as f:
            job_desc = f.read()
    else:
        job_desc = args.job_description
    
    # Perform analysis
    result = resume_job_match_analysis(args.resume_file, job_desc)
    
    if result:
        # Save results if output specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Analysis saved to {args.output}")
        
        # Generate report if requested
        if args.report:
            report = generate_hiring_report(result)
            with open(args.report, 'w') as f:
                f.write(report)
            print(f"Hiring report saved to {args.report}")
        
        # Print summary
        print(f"Match Score: {result.get('match_score', 'N/A')}/100")
        print(f"Match Label: {result.get('match_label', 'Unknown')}")
        print(f"Summary: {result.get('summary', 'No summary available')}")
    else:
        print("Analysis failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())