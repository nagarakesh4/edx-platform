from pynodebb.api.categories import Category


class ForumCategory(Category):
    """
    Added custom methods to the default Category class of pynodebb package
    """

    def create(self, name, label, hidden=1, uid=1, parent_cid=None, description='', **kwargs):
        """
         Create a private category on NodeBB

         **Accepted parameters**
            * parentCid: for creating team subcategory
        """
        payload = {
            'name': name,
            'label': label,
            '_uid': uid,
            'hidden': hidden,
            'parentCid': parent_cid,
            'description': description
        }
        return self.client.post('/api/v2/category/private', **payload)

    def featured(self, **kwargs):
        """
        Get all the featured categories from NodeBB
        """
        return self.client.get('/api/v2/category/featured', **kwargs)

    def recommended(self, username, **kwargs):
        """
        Get recommended categories for a specific user
        """
        payload = {'username': username}
        return self.client.post('/api/v2/category/recommended', **payload)

    def joined(self, username, **kwargs):
        """
        Get joined categories for a specific user
        """
        payload = {'username': username}
        return self.client.post('/api/v2/category/joined', **payload)

    def delete(self, category_id, **kwargs):
        """
        Delete a category from NodeBB, including all topics and posts inside of it (Careful: There is no confirmation!)
        :param category_id: Id of the NodeBB category
        :return:
            * 200 status if successful
        """
        return self.client.delete('/api/v2/categories/{}'.format(category_id))

    def join(self, username, category_id, **kwargs):
        """
        Join category for specific user
        :param username: username of the logged in user
        :param category_id: Id of the NodeBB category
        :return:
            * 200 status if successful
            * 401 if user is unauthorized
            * 400 if bad request
        """

        payload = {
            'username': username,
            'category_id': category_id
        }
        return self.client.post('api/v2/users/join', **payload)

    def leave(self, username, category_id, **kwargs):
        """
        Leave a category for some user
        :param username: username of logged in user
        :param category_id: Id of the NodeBB category
        :return:
            * 200 status if successfull
            * 401 if user is unauthorized
            * 400 if bad request
        """

        payload = {
            'username': username,
            'category_id': category_id
        }
        return self.client.post('api/v2/users/unjoin', **payload)
