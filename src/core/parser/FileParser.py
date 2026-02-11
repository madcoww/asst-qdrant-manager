"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

import csv
import json
import re
from io import StringIO

import aiofiles
import opendataloader_pdf
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.common.LoggerManager import LoggerManager


class FileParser:
    def __init__(self):
        self.logger = LoggerManager().get()

    async def process_json_file(self, file_path: str) -> list[dict]:
        """JSON 파일을 스트리밍 방식으로 읽어서 딕셔너리 리스트로 반환"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            data = json.loads(content)
            if not isinstance(data, list):
                data = [data]
            self.logger.info(f"Processed JSON file: {len(data)} records")
            return data
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {str(e)}")
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            self.logger.error(f"JSON processing error: {str(e)}")
            raise ValueError(f"Failed to process JSON file: {str(e)}")

    async def process_jsonl_file(self, file_path: str) -> list[dict]:
        """JSONL 파일을 라인별 스트리밍 방식으로 처리 (대용량 파일 지원)"""
        data: list[dict] = []
        line_num: int = 0

        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                while True:
                    line: str = await f.readline()
                    if not line:  # EOF
                        break

                    line_num += 1
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        item: dict = json.loads(line)
                        data.append(item)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Skipping invalid JSON at line {line_num}: {str(e)}")
                        continue

            self.logger.info(f"Processed JSONL file: {len(data)} records from {line_num} lines")
            return data
        except Exception as e:
            self.logger.error(f"JSONL processing error: {str(e)}")
            raise ValueError(f"Invalid JSONL format: {str(e)}")

    async def process_csv_file(self, file_path: str) -> list[dict]:
        """CSV 파일을 스트리밍 방식으로 읽어서 딕셔너리 리스트로 반환"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                text_content = await f.read()

            csv_file = StringIO(text_content)
            reader = csv.DictReader(csv_file)
            self.logger.info(f"CSV columns: {reader.fieldnames}")
            data = list(reader)
            self.logger.info(f"Processed CSV file: {len(data)} records")
            return data
        except Exception as e:
            self.logger.error(f"CSV processing error: {str(e)}")
            raise ValueError(f"Invalid CSV format: {str(e)}")

    async def process_txt_file(
            self,
            file_path: str,
            chunk_size: int,
            chunk_overlap: int,
    ) -> list[dict]:
        """TXT 파일을 청크 단위로 처리"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                text: str = await f.read()

            if not text or not text.strip():
                self.logger.warning(f"Empty TXT file: {file_path}")
                return []

            # 개선된 구분자 설정
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=[
                    '\n\n\n',  # 여러 빈 줄 (섹션 구분)
                    '\n\n',    # 문단 구분
                    '\n',      # 줄바꿈
                    '. ',      # 문장 끝
                    '! ',      # 느낌표
                    '? ',      # 물음표
                    '; ',      # 세미콜론
                    ', ',      # 쉼표
                    ' ',       # 공백
                    '',        # 문자 단위 (최후)
                ],
                length_function=len,
                keep_separator=True,  # 구분자 유지
            )

            chunks: list[Document] = text_splitter.create_documents([text])

            chunks_with_metadata: list[dict] = []
            for idx, chunk in enumerate(chunks):
                chunks_with_metadata.append({
                    'chunk_id': idx,
                    'text': chunk.page_content,
                    'metadata': {},
                })

            self.logger.info(
                f"Processed TXT file: {len(chunks_with_metadata)} chunks "
                f"(chunk_size={chunk_size}, overlap={chunk_overlap})",
            )
            return chunks_with_metadata

        except Exception as e:
            self.logger.error(f"TXT processing error: {str(e)}")
            raise ValueError(f"Invalid TXT format: {str(e)}")

    async def process_pdf_file(self, file_path: str, chunk_size: int, chunk_overlap: int) -> list[dict]:
        """
        PDF 파일을 마크다운으로 변환 후 청크 단위로 처리
        """
        try:
            # PDF → MD 변환
            opendataloader_pdf.run(
                input_path=file_path,
                replace_invalid_chars=' ',
                generate_markdown=True,
            )

            # MD 파일 경로 생성
            md_file_path: str = file_path.replace('.pdf', '.md')
            self.logger.info(f"PDF converted to markdown: {md_file_path}")

            # MD 파일 읽기
            markdown_content: str = await self._read_markdown_file(md_file_path)

            # 전처리
            preprocessed_content: str = self._preprocess_markdown(markdown_content)

            # 청킹
            chunks: list[dict] = self._chunk_markdown(
                content=preprocessed_content,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            self.logger.info(
                f"Successfully processed {file_path}: {len(chunks)} chunks created",
            )
            return chunks

        except Exception as e:
            self.logger.error(f"PDF processing error: {str(e)}")
            raise ValueError(f"Invalid PDF format: {str(e)}")

    async def _read_markdown_file(self, file_path: str) -> str:
        """마크다운 파일을 비동기적으로 읽어서 문자열로 반환"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            self.logger.info(f"Read markdown file: {file_path}")
            return content
        except Exception as e:
            self.logger.error(f"Markdown reading error: {str(e)}")
            raise ValueError(f"Failed to read markdown file: {str(e)}")

    @staticmethod
    def _preprocess_markdown(content: str) -> str:
        """마크다운 컨텐츠 전처리"""
        # 모든 이미지 마크다운 제거 (빈 것 포함)
        content = re.sub(r'!\[.*?]\(.*?\)', '', content)

        # 여러 개의 연속된 빈 줄을 두 개로 제한
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()

    @staticmethod
    def _chunk_markdown(content: str, chunk_size: int, chunk_overlap: int) -> list[dict]:
        """마크 다운 컨텐츠를 청크 단위로 분할하여 반환"""
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ('#', 'h1'),
                ('##', 'h2'),
                ('###', 'h3'),
            ],
            strip_headers=False,
        )
        header_chunks: list[Document] = header_splitter.split_text(content)

        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=['\n\n', '\n', ' ', ''],
        )

        final_chunks: list[Document] = recursive_splitter.split_documents(header_chunks)

        chunks_with_metadata: list[dict] = []

        for idx, chunk in enumerate(final_chunks):
            chunks_with_metadata.append({
                'chunk_id': idx,
                'text': chunk.page_content,
                'metadata': {
                    'h1': chunk.metadata.get('h1', ''),
                    'h2': chunk.metadata.get('h2', ''),
                    'h3': chunk.metadata.get('h3', ''),
                },
            })

        return chunks_with_metadata
