import hashlib
import time

class Block:
    def __init__(self, transaction, prev_hash):
        self.transaction = transaction
        self.prev_hash = prev_hash
        self.created_at = str(time.time())
        self.nonce = 0
        # ブロック固有のハッシュ値を計算
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        """ transaction + prev_hash + created_at からハッシュを計算 """
        data = str(self.transaction) + str(self.prev_hash) + str(self.created_at)
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def mine(self, difficulty):
        """ PoW: hash(ブロックハッシュ + nonce) の先頭が 0 * difficulty になるまで計算 """
        target = '0' * difficulty
        start_time = time.time()
        while True:
            data_to_hash = str(self.hash) + str(self.nonce)
            pow_hash = hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()
            
            if pow_hash.startswith(target): # つまり、0000から始まってたら
                end_time = time.time()
                elapsed_time = end_time - start_time
                print(f"Block mined! Nonce: {self.nonce}, PoW Hash: {pow_hash}")
                print(f"マイニング時間: {elapsed_time:.4f} 秒")
                break
            self.nonce += 1

    def is_valid_pow(self, difficulty):
        """ ブロックのPoW条件が満たされているか検証 """
        target = '0' * difficulty
        data_to_hash = str(self.hash) + str(self.nonce)
        pow_hash = hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()
        return pow_hash.startswith(target)

    def to_dict(self):
        return {
            'transaction': self.transaction,
            'prev_hash': self.prev_hash,
            'created_at': self.created_at,
            'nonce': self.nonce,
            'hash': self.hash
        }

    @classmethod
    def from_dict(cls, data):
        block = cls(data['transaction'], data['prev_hash'])
        block.created_at = data['created_at']
        block.nonce = data['nonce']
        block.hash = data['hash']
        return block


class Blockchain:
    def __init__(self, difficulty=4):
        self.chain = []
        self.difficulty = difficulty
        self.create_genesis_block()

    def create_genesis_block(self):
        """ 最初のブロック（ジェネシスブロック）を作成 """
        genesis_block = Block("Genesis Block", "0")
        genesis_block.created_at = "1700000000.000000" # 全ノードでハッシュを一致させるため固定
        genesis_block.hash = genesis_block.calculate_hash() # タイムスタンプ変更後にハッシュを再計算
        genesis_block.mine(self.difficulty)
        self.chain.append(genesis_block)

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, transaction):
        """ 新しいブロックを追加（マイニングを含む） """
        prev_block = self.get_latest_block()
        new_block = Block(transaction, prev_block.hash)
        new_block.mine(self.difficulty)
        self.chain.append(new_block)

    def is_valid(self):
        """ チェーン全体の改ざんがないか検証する """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            prev_block = self.chain[i-1]

            # 1. 記録されているハッシュ値と再計算したハッシュ値が一致するか（改ざん検知）
            if current_block.hash != current_block.calculate_hash():
                print(f"Validation Error: Block {i} のデータが改ざんされています。")
                return False

            # 2. prev_hash が前のブロックのハッシュと一致するか（チェーンの切断検知）
            if current_block.prev_hash != prev_block.hash:
                print(f"Validation Error: Block {i} の prev_hash が不整合です。")
                return False

            # 3. PoWの条件を満たしているか
            if not current_block.is_valid_pow(self.difficulty):
                print(f"Validation Error: Block {i} のマイニング条件が満たされていません。")
                return False

        # ジェネシスブロックの検証も行う
        if self.chain[0].hash != self.chain[0].calculate_hash() or not self.chain[0].is_valid_pow(self.difficulty):
             print("Validation Error: Genesis Block が不正です。")
             return False

        return True

    def get_chain_data(self):
        return [block.to_dict() for block in self.chain]

    def replace_chain(self, chain_data):
        """ 新しいチェーンデータを受け取り、より長くて妥当なら置き換える（最長チェーン選択アルゴリズム） """
        new_chain = [Block.from_dict(b_data) for b_data in chain_data]
        
        # 現在のチェーンより長いか確認
        if len(new_chain) <= len(self.chain):
            return False
            
        # 一時的に置き換えて妥当性検証
        original_chain = self.chain
        self.chain = new_chain
        if self.is_valid():
            return True
        else:
            # 不正なチェーンだった場合は元に戻す
            self.chain = original_chain
            return False
