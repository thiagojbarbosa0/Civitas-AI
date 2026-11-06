"""SFT demonstrativo com LoRA (PEFT). Opcional; não participa do serviço HTTP.

Este script NÃO executa automaticamente. Requer downloads de pesos e recursos
computacionais apropriados. Dados são fictícios. Não usar como modelo oficial.
"""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description='Treinamento LoRA demonstrativo, em dados fictícios')
    p.add_argument('--model', default='Qwen/Qwen2.5-0.5B-Instruct')
    p.add_argument('--data', default=str(Path(__file__).with_name('samples.jsonl')))
    p.add_argument('--output', default='training/output/civitas-lora')
    p.add_argument('--epochs', type=float, default=1)
    p.add_argument('--max-length', type=int, default=512)
    p.add_argument('--dry-run', action='store_true', help='Validar dataset sem baixar pesos nem instalar ML')
    args = p.parse_args()

    # Dry run de validação isolado: executável no CI sem GPU, pesos ou dependências ML.
    data_path = Path(args.data)
    records = [json.loads(l) for l in data_path.read_text(encoding='utf-8').splitlines() if l.strip()]
    if not records or any(not isinstance(r.get('instruction'), str) or not r['instruction'].strip()
                          or not isinstance(r.get('response'), str) or not r['response'].strip()
                          for r in records):
        raise ValueError('Dataset inválido: instruction e response devem ser strings não vazias')
    if len({r['instruction'] for r in records}) != len(records):
        raise ValueError('Dataset contém instruções duplicadas')
    if args.dry_run:
        print(f'Dataset válido: {len(records)} exemplos; treino não executado.')
        return

    import torch
    from torch.utils.data import Dataset
    from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
    from peft import LoraConfig, get_peft_model

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model)
    model.config.use_cache = False
    lora = LoraConfig(r=8, lora_alpha=16, lora_dropout=.05, bias='none', task_type='CAUSAL_LM',
                      target_modules=['q_proj', 'v_proj'])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()


    class Examples(Dataset):
        def __len__(self):
            return len(records)

        def __getitem__(self, idx):
            rec = records[idx]
            prompt = ('Você é um assistente de cidade fictícia. Não invente serviços reais.\n'
                      f'Pergunta: {rec["instruction"]}\nResposta: ')
            full = prompt + rec['response'] + (tokenizer.eos_token or '')
            encoded = tokenizer(full, truncation=True, max_length=args.max_length, add_special_tokens=True)
            prefix = tokenizer(prompt, add_special_tokens=True)['input_ids']
            labels = encoded['input_ids'].copy()
            labels[:min(len(prefix), len(labels))] = [-100]*min(len(prefix), len(labels))
            return {'input_ids': encoded['input_ids'], 'attention_mask': encoded['attention_mask'], 'labels': labels}

    def collate(batch):
        max_len = max(len(x['input_ids']) for x in batch)
        return {
            'input_ids': torch.tensor([x['input_ids'] + [tokenizer.pad_token_id]*(max_len-len(x['input_ids'])) for x in batch]),
            'attention_mask': torch.tensor([x['attention_mask'] + [0]*(max_len-len(x['input_ids'])) for x in batch]),
            'labels': torch.tensor([x['labels'] + [-100]*(max_len-len(x['labels'])) for x in batch]),
        }

    train_args = TrainingArguments(output_dir=args.output, num_train_epochs=args.epochs,
                                  per_device_train_batch_size=1, gradient_accumulation_steps=2,
                                  learning_rate=2e-4, logging_steps=1, save_strategy='epoch',
                                  report_to='none', fp16=False, bf16=False)
    trainer = Trainer(model=model, args=train_args, train_dataset=Examples(), data_collator=collate)
    trainer.train()
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print('Adapter LoRA salvo em', args.output)
    print('ATENÇÃO: adapter experimental; não integrado automaticamente à API de inferência.')


if __name__ == '__main__':
    main()
